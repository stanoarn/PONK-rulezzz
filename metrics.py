from __future__ import annotations
from udapi.core.document import Document
from udapi.core.node import Node

from typing import Iterator, Tuple, List, Literal, Union

from math import log2

from utils import StringBuildable

from pydantic import BaseModel, Field


class Metric(StringBuildable):
    #TODO: figure out how to enforce rule_id presence

    def apply(self, doc: Document) -> float:
        raise NotImplementedError(f"Please define your metric's ({self.__class__.__name__}) apply method.")

    @staticmethod
    def get_word_counts(doc: Document, use_lemma=False, filter_punct=True, from_to: Tuple[int,int] | None = None) -> Iterator[Tuple[str, int]]:
        filtered_nodes = Metric.negative_filter_nodes_on_upos(doc.nodes, ['PUNCT'] if filter_punct else [])
        if from_to:
            filtered_nodes = filtered_nodes[from_to[0]:from_to[1]]
        all_words = Metric.get_node_texts(filtered_nodes, use_lemma)
        unique_words = set(all_words)
        counts = map(lambda x: all_words.count(x), unique_words)
        return zip(unique_words, counts)

    @staticmethod
    def filter_nodes_on_upos(nodes: Iterator[Node], values: List[str], negative=False) -> List[Node]:
        return [node for node in nodes if ((node.upos in values) != negative)]

    @staticmethod
    def negative_filter_nodes_on_upos(nodes: Iterator[Node], values_to_exclude: List[str]) -> List[Node]:
        return Metric.filter_nodes_on_upos(nodes, values_to_exclude, True)

    @staticmethod
    def get_node_texts(nodes: Iterator[Node], use_lemma=False):
        return [node.form if not use_lemma else node.lemma for node in nodes]

    @staticmethod
    def get_syllables_in_word(word: str) -> int:
        #FIXME: eeeeeh
        return sum([word.count(vocal) for vocal in ('a', 'e', 'i', 'o', 'u', 'y')])


class SentenceCount(Metric):
    rule_id: Literal['sent_count'] = 'sent_count'

    def apply(self, doc: Document) -> float:
        return len(doc.bundles)

    @classmethod
    def id(cls):
        return "sent_count"


class WordCount(Metric):
    rule_id: Literal['word_count'] = 'word_count'
    filter_punct: bool = True

    def apply(self, doc: Document) -> float:
        return len(Metric.negative_filter_nodes_on_upos(doc.nodes, ['PUNCT'] if self.filter_punct else []))

    @classmethod
    def id(cls):
        return "word_count"

class SyllableCount(Metric):
    rule_id: Literal['syllab_count'] = 'syllab_count'
    filter_punct: bool = True

    def apply(self, doc: Document) -> float:
        filtered_nodes = Metric.negative_filter_nodes_on_upos(doc.nodes, ['PUNCT'] if self.filter_punct else [])
        return sum(Metric.get_syllables_in_word(node.form) for node in filtered_nodes)

    @classmethod
    def id(cls):
        return "syllab_count"

class CharacterCount(Metric):
    rule_id: Literal['char_count'] = 'char_count'
    count_spaces: bool = False
    filter_punct: bool = True

    def apply(self, doc: Document) -> float:
        filtered_nodes = Metric.negative_filter_nodes_on_upos(doc.nodes, ['PUNCT'] if self.filter_punct else [])
        return sum(len(node.form) for node in filtered_nodes) + \
            (len(filtered_nodes) if self.count_spaces else 0)  # TODO:fix this via reading mics

    @classmethod
    def id(cls):
        return "char_count"


class CLI(Metric):
    rule_id: Literal['cli'] = 'cli'
    count_spaces: bool = False
    filter_punct: bool = True
    coef_1: float = 0.047
    coef_2: float = 0.286
    const_1: float = 12.9

    def apply(self, doc: Document) -> float:
        sents = SentenceCount().apply(doc)
        words = WordCount(filter_punct=self.filter_punct).apply(doc)
        chars = CharacterCount(count_spaces=self.count_spaces, filter_punct=self.filter_punct).apply(doc)
        return (self.coef_1 * (chars/words) * 100) - (self.coef_2 * (sents/words) * 100) - self.const_1

    @classmethod
    def id(cls):
        return "cli"


class ARI(Metric):
    rule_id: Literal['ari'] = 'ari'
    count_spaces: bool = False
    filter_punct: bool = True
    coef_1: float = 3.666
    coef_2: float = 0.631
    const_1: float = 19.49

    def apply(self, doc: Document) -> float:
        sents = SentenceCount().apply(doc)
        words = WordCount(filter_punct=self.filter_punct).apply(doc)
        chars = CharacterCount(count_spaces=self.count_spaces, filter_punct=self.filter_punct).apply(doc)
        return self.coef_1 * (chars/words) + self.coef_2 * (words/sents) - self.const_1

    @classmethod
    def id(cls):
        return "ari"


class HapaxCount(Metric):
    rule_id: Literal['num_hapax'] = 'num_hapax'
    use_lemma: bool = True

    def apply(self, doc: Document) -> float:
        counts = [item[1] for item in super().get_word_counts(doc, self.use_lemma)]
        return counts.count(1)

    @classmethod
    def id(cls):
        return "num_hapax"


class Entropy(Metric):
    rule_id: Literal['entropy'] = 'entropy'
    use_lemma: bool = True

    def apply(self, doc: Document) -> float:
        counts = [item[1] for item in self.get_word_counts(doc, self.use_lemma)]
        n_words = sum(counts)
        probs = map(lambda x: x/n_words, counts)
        return -sum(prob * log2(prob) for prob in probs)

    @classmethod
    def id(cls):
        return "entropy"


class TTR(Metric):
    rule_id: Literal['ttr'] = 'ttr'
    filter_punct: bool = True

    def apply(self, doc: Document) -> float:
        counts = dict(Metric.get_word_counts(doc, use_lemma=True, filter_punct=self.filter_punct))
        return len(counts) / sum(count for lemma, count in counts.items())

    @classmethod
    def id(cls):
        return "ttr"


class VerbDistance(Metric):
    rule_id: Literal['verb_dist'] = 'verb_dist'
    include_inf: bool = True

    def apply(self, doc: Document) -> float:
        last_verb_index = 0
        total_distance = 0
        verbs = 0
        nodes = list(doc.nodes)
        # FIXME: iterate over trees
        for i in range(len(nodes)):
            node = nodes[i]
            if node.upos == 'VERB' and (self.include_inf or node.feats['VerbForm'] == 'Fin'):
                total_distance += max(0, (i - last_verb_index - 1))
                last_verb_index = i
                verbs += 1
        total_distance += len(nodes) - last_verb_index
        return total_distance / verbs

    @classmethod
    def id(cls):
        return 'verb_distance'

class Activity(Metric):
    rule_id: Literal['activity'] = 'activity'

    def apply(self, doc: Document) -> float:
        nodes = list(doc.nodes)
        return len(Metric.filter_nodes_on_upos(nodes, ['VERB'])) /\
            len(Metric.filter_nodes_on_upos(nodes, ['VERB', 'ADJ']))

    @classmethod
    def id(cls):
        return 'activity'


class HPoint(Metric):
    rule_id: Literal['hpoint'] = 'hpoint'
    use_lemma: bool = True
    filter_punct: bool = True

    def apply(self, doc: Document) -> float:
        counts = [item[1] for item in self.get_word_counts(doc, self.use_lemma, self.filter_punct)]
        counts.sort(reverse=True)
        for i in range(len(counts)):
            if i+1 == counts[i]:
                return counts[i]
            if i+1 > counts[i]:
                i = i - 1
                j = i + 1
                fi = counts[i]
                fj = counts[j]
                return (fi * j - fj * i) / (j - i + fi - fj)
        return 0

    @classmethod
    def id(cls):
        return "hpoint"


class AverageTokenLength(Metric):
    rule_id: Literal['atl'] = 'atl'
    filter_punct: bool = True

    def apply(self, doc: Document) -> float:
        total_tokens = WordCount(filter_punct=self.filter_punct).apply(doc)
        total_chars = CharacterCount(filter_punct=self.filter_punct).apply(doc)
        return total_chars / total_tokens

    @classmethod
    def id(cls):
        return "atl"


class MovingAverageTypeTokenRatio(Metric):
    rule_id: Literal['mattr'] = 'mattr'
    use_lemma: bool = True
    filter_punct: bool = True
    window_size: int = 100

    def apply(self, doc: Document) -> float:
        #FIXME: this is horribly slow
        total_words = WordCount(filter_punct=self.filter_punct).apply(doc)
        big_sum = 0
        for i in range(int(total_words) - self.window_size):
            counts = dict(Metric.get_word_counts(doc,
                                                 use_lemma=self.use_lemma,
                                                 filter_punct=self.filter_punct,
                                                 from_to=(i, i+self.window_size)
                                                 ))
            big_sum += len(counts)
            print(big_sum)

        return big_sum / (self.window_size * (total_words - self.window_size + 1))

    @classmethod
    def id(cls):
        return "mattr"


class MovingAverageMorphologicalRichness(Metric):
    rule_id: Literal['mamr'] = 'mamr'
    filter_punct: bool = True
    window_size: int = 100

    def apply(self, doc: Document) -> float:
        return MovingAverageTypeTokenRatio(use_lemma=False,
                                           filter_punct=self.filter_punct,
                                           window_size=self.window_size).apply(doc) - \
               MovingAverageTypeTokenRatio(use_lemma=True,
                                           filter_punct=self.filter_punct,
                                           window_size=self.window_size).apply(doc)

    @classmethod
    def id(cls):
        return "mamr"


class FleschReadingEase(Metric):
    rule_id: Literal['fre'] = 'fre'
    count_spaces: bool = False
    filter_punct: bool = True
    coef_1: float = 1.672
    coef_2: float = 62.18
    const_1: float = 206.935

    def apply(self, doc: Document) -> float:
        sents = SentenceCount().apply(doc)
        words = WordCount(filter_punct=self.filter_punct).apply(doc)
        syllabs = SyllableCount(filter_punct=self.filter_punct).apply(doc)
        return self.const_1 - self.coef_1 * (words / sents) - self.coef_2 * (syllabs / words)

    @classmethod
    def id(cls):
        return "fre"


class FleschKincaidGradeLevel(Metric):
    rule_id: Literal['fkgl'] = 'fkgl'
    count_spaces: bool = False
    filter_punct: bool = True
    coef_1: float = 0.52
    coef_2: float = 9.133
    const_1: float = 16.393

    def apply(self, doc: Document) -> float:
        sents = SentenceCount().apply(doc)
        words = WordCount(filter_punct=self.filter_punct).apply(doc)
        syllabs = SyllableCount(filter_punct=self.filter_punct).apply(doc)
        return  self.coef_1 * (words / sents) + self.coef_2 * (syllabs / words) - self.const_1

    @classmethod
    def id(cls):
        return "fkgl"
# = 0.52 ×T okens/Sentences + 9.133 × Syllables/T okens − 16.393


print(Metric.__subclasses__() == Metric.get_final_children())


class MetricsWrapper(BaseModel):
    metric: Union[*Metric.get_final_children()] = Field(..., discriminator='rule_id')

