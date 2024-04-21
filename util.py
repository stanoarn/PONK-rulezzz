from udapi.core.node import Node
from udapi.core.dualdict import DualDict

import re


def node_is(node: Node, *matches: tuple[str, str | None]) -> bool:
    for match in matches:
        if match[1] is None:
            if getattr(node, match[0]) is None:
                return False
        elif not re.search(match[1], getattr(node, match[0])):
            return False
    return True


def find_nodes(nodes: list[Node], *matches: tuple[str, str]) -> list[Node]:
    res = []
    for node in nodes:
        if node_is(node, *matches):
            res += [node]
    return res


def clone_node(node: Node, parent: Node, filter_misc_keys: str = None, **override) -> Node:
    res = parent.create_child(
        form=node.form,
        lemma=node.lemma,
        upos=node.upos,
        xpos=node.xpos,
        feats=node.feats,
        deprel=node.deprel,
        misc=node.misc,
    )

    if filter_misc_keys:
        res.misc = DualDict({k: v for k, v in node.misc.items() if re.search(filter_misc_keys, k)})

    for arg, val in override.items():
        setattr(res, arg, val)

    return res


def is_aux(node: Node, grammatical_only: bool = False) -> bool:
    if grammatical_only:
        return node.udeprel in ('aux', 'cop') or node.deprel == 'expl:pass'
    else:
        return node.udeprel in ('aux', 'expl', 'cop')


def is_finite_verb(node: Node) -> bool:
    return ('VerbForm' in node.feats and node.feats['VerbForm'] == 'Fin') or node.xpos[0:2] == 'Vp'


def is_clause_root(node: Node) -> bool:
    return (
        node.udeprel in ('csubj', 'ccomp', 'xcomp', 'acl', 'advcl', 'parataxis', 'root')
        or is_finite_verb(node)
        or [nd for nd in node.children if is_aux(nd, grammatical_only=True)]
    )


def get_clause_root(node: Node) -> Node:
    clause_root = node
    while not is_clause_root(clause_root):
        clause_root = clause_root.parent
    return clause_root


def get_clause(
    node: Node,
    without_subordinates: bool = False,
    without_punctuation: bool = False,
    node_is_root: bool = False,
) -> list[Node]:
    clause_root = node if node_is_root else get_clause_root(node)
    clause = clause_root.descendants(add_self=True)

    if without_subordinates:
        to_remove = []
        for nd in clause:
            if nd == clause_root:
                continue

            if is_clause_root(nd):
                to_remove += nd.descendants(add_self=True)

        clause = [nd for nd in clause if not nd in to_remove]

    if without_punctuation:
        clause = [nd for nd in clause if nd.upos != 'PUNCT']

    return clause
