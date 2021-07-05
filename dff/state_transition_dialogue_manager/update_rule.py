# import regex
from dff.state_transition_dialogue_manager.natex_nlu import NatexNLU
from dff.state_transition_dialogue_manager.natex_nlg import NatexNLG


class UpdateRule:
    def __init__(self, precondition, postcondition="", vars=None, macros=None):
        self.precondition = None
        self.precondition_score = 1.0
        self.postcondition = None
        self.postcondition_score = None
        self.is_repeating = len(precondition) > 0 and precondition[0] == "*"
        if self.is_repeating:
            precondition = precondition[1:]
        if macros is None:
            macros = {}
        if vars is None:
            vars = {}
        self.vars = vars
        self.macros = macros
        self.set_precondition(precondition)
        if postcondition:
            self.set_postcondition(postcondition)

    def set_precondition(self, natex_string):
        natex, score = self._natex_string_score(natex_string)
        self.precondition = NatexNLU(natex, macros=self.macros)
        if score:
            self.precondition_score = score

    def set_postcondition(self, natex_string):
        natex, score = self._natex_string_score(natex_string)
        self.postcondition = NatexNLG(natex, macros=self.macros)
        self.postcondition_score = score

    def _natex_string_score(self, natex_string):
        i = natex_string.rfind(" (")
        if i != -1:
            for c in natex_string[i + len(" (") : -1]:
                if c not in set("0123456789."):
                    return natex_string, None
            return natex_string[:i], float(natex_string[i + len(" (") : -1])
        return natex_string, None

    def satisfied(self, user_input, vars, debugging=False):
        return self.precondition.match(user_input, vars=vars, debugging=debugging)

    def apply(self, vars, debugging=False):
        if self.postcondition is not None:
            return self.postcondition.generate(vars=vars, debugging=debugging)
        else:
            return ""

    def set_vars(self, vars):
        self.vars = vars

    def __str__(self):
        return "{} ==> {}".format(self.precondition, self.postcondition)

    def __repr__(self):
        return str(self)
