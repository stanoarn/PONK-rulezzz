from document_applicables.rules import *
profiles = {
    'default': (None, None),
    'minimal': (None,  # default metrics
                [RuleDoubleAdpos(max_allowable_distance=0),
                 RulePassive(),
                 RulePredSubjDistance(max_distance=0),
                 RulePredObjDistance(max_distance=0),
                 RuleInfVerbDistance(max_distance=0),
                 RuleMultiPartVerbs(max_distance=0),
                 RuleLongSentences(max_length=0),
                 RulePredAtClauseBeginning(max_order=0),
                 RuleVerbalNouns(),
                 RuleTooFewVerbs(min_verb_frac=1),
                 RuleTooManyNegations(max_allowable_negations=0),
                 RuleWeakMeaningWords(),
                 RuleAbstractNouns(),
                 RuleRelativisticExpressions(),
                 RuleConfirmationExpressions(),
                 RuleRedundantExpressions(),
                 RuleTooLongExpressions(),
                 RuleAnaphoricReferences(),
                 RuleAmbiguousRegards(),
                 ]
                )
}