from abc import ABC, abstractmethod  # , abstractproperty
from dff.state_transition_dialogue_manager.ngrams import Ngrams
from typing import List, Dict, Any  #  , Union, Set, Callable, Tuple, NoReturn


class Macro(ABC):
    @abstractmethod
    def run(self, ngrams: Ngrams, vars: Dict[str, Any], args: List[Any]):
        """
        :param ngrams: an Ngrams object defining the set of all ngrams in the
                       input utterance (for NLU) or vocabulary (for NLG). Treat
                        like a set for all ngrams, or get a specific ngram set
                        using ngrams[n]. Get original string using .text()
        :param vars: a reference to the dictionary of variables
        :param args: a list of arguments passed to the macro from the Natex
        :returns: string, set, boolean, or arbitrary object
                  returning a string will replace the macro call with that string
                  in the natex
                  returning a set of strings replaces macro with a disjunction
                  returning a boolean will replace the macro with wildcards (True)
                  or an unmatchable character sequence (False)
                  returning an arbitrary object is only used to pass data to other macros
        """
        pass

    def debugging_on(self):
        self.debugging = True

    def __call__(self, *args, **kwargs):
        return self.run(*args, **kwargs)
