from dff.state_transition_dialogue_manager.macro import Macro
from typing import List, Any, Dict  # , Union, Set, Callable, Tuple, NoReturn
from dff.state_transition_dialogue_manager.ngrams import Ngrams
from dff.state_transition_dialogue_manager.natex_nlu import NatexNLU

# from dff.state_transition_dialogue_manager import macros_common as mc
import random


def CommonNatexMacro(natex_string):
    class _CommonNatex(Macro):
        def __init__(self, macro_dependencies=None):
            if macro_dependencies is None:
                macro_dependencies = {}
            self.natex = NatexNLU(natex_string, macros={**macro_dependencies})
            self.natex.compile()
            self.natex._regex = self.natex.regex().replace("_END_", "").strip()

        def run(self, ngrams: Ngrams, vars: Dict[str, Any], args: List[Any]):
            return self.natex.regex()

    return _CommonNatex


def NatexMacro(natex_string):
    class _CommonNatex(Macro):
        def __init__(self, macro_dependencies=None):
            if macro_dependencies is None:
                macro_dependencies = {}
            self.natex = NatexNLU(natex_string, macros={**macro_dependencies})
            self.natex.precache()

        def run(self, ngrams: Ngrams, vars: Dict[str, Any], args: List[Any]):
            match = self.natex.match(ngrams.text(), vars=vars)
            return bool(match)

    return _CommonNatex


agree = (
    "[! -not {"
    "sure, i know,"
    "[{yes, yeah, yea, yep, yup, think so, i know, absolutely, exactly, precisely, "
    "certainly, surely, definitely, probably, true, of course, right}]"
    "}]"
)
Agree = CommonNatexMacro(agree)

disagree = (
    "{"
    + ", ".join(
        [
            "[{no, nay, nah, na, not really, nope, no way, wrong}]",
            "[{absolutely, surely, definitely, certainly, i think} not]",
            "[i, do not, think so]",
            "[not true]",
        ]
    )
    + "}"
)
Disagree = CommonNatexMacro(disagree)

question = (
    "{[!/([^ ]+)?/ {who, what, when, where, why, how} /.*/], "
    "[!{is, does, can, could, should, "
    '"isnt", "shouldnt", "couldnt", "cant", "aint", "dont", do,'
    'did, was, were, will, "wasnt", "werent", "didnt", has, had, have} /.*/]}'
)
Question = CommonNatexMacro(question)

negation = (
    '{not, "dont", "cant", "wont", "shouldnt", "cannot", "didnt", "doesnt",'
    ' "isnt", "couldnt", "havent", "arent", "never", "impossible", "unlikely", '
    '"no way", "none", "nothing"}'
)
Negation = CommonNatexMacro(negation)

confirm = (
    "{%s, [!-{%s, %s} [{okay, ok, alright, all right, right, i understand, "
    "i see, got it, makes sense, understood, sounds good, perfect}]]}" % (agree, disagree, negation)
)
Confirm = CommonNatexMacro(confirm)

dont_know = (
    "[{"
    "dont know,do not know,unsure,[not,{sure,certain}],hard to say,no idea,uncertain, "
    "[!no {opinion,opinions,idea,ideas,thought,thoughts,knowledge}],"
    "[{dont,do not}, have, {opinion,opinions,idea,ideas,thought,thoughts,knowledge}],"
    "[!{cant,cannot,dont} {think,remember,recall}]"
    "}]"
)
DontKnow = CommonNatexMacro(dont_know)

maybe = "[{maybe,possibly,sort of,kind of,kinda,a little,at times,sometimes,could be,potentially,its possible}]"
Maybe = CommonNatexMacro(dont_know)

unintrerested = "[!-oh #TOKLIMIT(3) [{okay, sure, alright, all right, fine, um}]]"
Uninterested = NatexMacro(unintrerested)

notinterested = (
    "{[i, not, care], um? {so, so what, big deal, what, no}, "
    "[!#TOKLIMIT(3) [{weird, strange, dumb, stupid, boring, dull}]]}"
)
NotInterested = NatexMacro(notinterested)

interested = (
    "{[!-not [{great, good, cool, awesome, nice, sweet, wonderful, amazing, fun, "
    "wow, my god, woah, interesting, oh}]], really}"
)
Interested = CommonNatexMacro(interested)

decline_share = "{" "[not, #LEM(talk,discuss,share,give,tell,say)]," "[none,your,business]," "[that is private]" "}"
DeclineShare = CommonNatexMacro(decline_share)


class Unexpected(Macro):
    def __init__(self):
        self.question_natex = NatexNLU(question)

    def run(self, ngrams: Ngrams, vars: Dict[str, Any], args: List[Any]):
        statement_only = "s" in args or "state" in args or "statement" in args
        vars["__score__"] = 0.0
        if "__previous_unx_response__" not in vars:
            vars["__previous_unx_response__"] = "Gotcha."
        if "__previous_unx_answer__" not in vars:
            vars["__previous_unx_answer__"] = "None"

        is_question = self.question_natex.match(ngrams.text())
        if is_question and statement_only:
            return False
        elif is_question:
            if "_explained_stupidity_" in vars and vars["_explained_stupidity_"] == "True":
                options = {
                    "I'm not sure.",
                    "I don't know.",
                    "I'm not sure about that.",
                    "",
                } - {vars["__previous_unx_response__"]}
                question_response = random.choice(list(options))
                vars["__previous_unx_answer__"] = question_response
                vars["__response_prefix__"] = question_response
            else:
                vars["_explained_stupidity_"] = "True"
                vars["__response_prefix__"] = "I'm not sure."
        elif len(ngrams.text().split()) < 3 and len(args) == 0:
            vars["__response_prefix__"] = ""
            return True
        else:
            options = {"Yeah.", "For sure.", "Right.", "Uh-huh."} - {vars["__previous_unx_response__"]}
            statement_response = random.choice(list(options))
            if len(args) > 0:
                statement_response = ", ".join([arg for arg in args if arg not in {"s", "state", "statement"}]) + ", "
                if args[0] == "None":
                    statement_response = ""
            vars["__previous_unx_response__"] = statement_response
            vars["__response_prefix__"] = statement_response
        return True


natex_macros_common = {
    "AGREE": Agree(),
    "DISAGREE": Disagree(),
    "QUESTION": Question(),
    "NEGATION": Negation(),
    "IDK": DontKnow(),
    "MAYBE": Maybe(),
    "CONFIRM": Confirm(),
    "UNINTERESTED": Uninterested(),
    "NOTINTERESTED": NotInterested(),
    "INTERESTED": Interested(),
    "UNX": Unexpected(),
    "PRIVATE": DeclineShare(),
}

if __name__ == "__main__":
    print(NatexNLU(question).match("i don't know"))
