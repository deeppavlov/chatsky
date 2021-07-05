import regex
from lark import Lark, Transformer, Tree, Visitor, Token
from dff.state_transition_dialogue_manager.ngrams import Ngrams
from dff.state_transition_dialogue_manager.utilities import HashableDict
from copy import deepcopy
import sys
import traceback


class NatexNLU:
    def __init__(self, expression, macros=None):
        self._regex = None
        if macros is None:
            macros = {}
        self._macros = macros
        if isinstance(expression, str):
            self._expression = expression
        elif isinstance(expression, list) or isinstance(expression, set):
            item = next(iter(expression))
            if isinstance(item, str):
                self._expression = "{" + ", ".join(expression) + "}"
            elif isinstance(item, NatexNLU):
                raise NotImplementedError()
        elif isinstance(expression, NatexNLU):
            self._expression = expression.expression()
            self._macros = dict(expression.macros())
            self._macros.update(macros)
        self._compiler = NatexNLU.Compiler(self._expression)

    def match(self, natural_language, vars=None, macros=None, ngrams=None, debugging=False):
        natural_language += " _END_"
        if vars is None:
            vars = HashableDict()
        original_vars = vars
        vars = HashableDict(vars)
        if ngrams is None:
            ngrams = Ngrams(natural_language)
        self.compile(ngrams, vars, macros, debugging)
        match = regex.fullmatch(self._regex, natural_language)
        self._regex = None
        if match:
            vars.update({k: v for k, v in match.groupdict().items() if v is not None})
            original_vars.update({k: vars[k] for k in vars})
        return match

    def compile(self, ngrams=None, vars=None, macros=None, debugging=False):
        if vars is None:
            vars = {}
        if macros is not None:
            for k, v in self._macros.items():
                if k not in macros:
                    macros[k] = v
        else:
            macros = self._macros
        if debugging:
            print("NatexNLU compilation:")
            print("  {:15} {}".format("Input", ngrams.text()))
            print("  {:15} {}".format("Macros", " ".join(macros.keys())))
            print("  {:15} {}".format("Vars", ", ".join([k + "=" + str(v) for k, v in vars.items()])))
            print("  {:15} {}".format("Steps", "  " + "-" * 60))
            print("    {:15} {}".format("Original", self._expression))
        self._regex = self._compiler.compile(ngrams, vars, macros, debugging)

    def precache(self):
        self._compiler.parse()

    def regex(self):
        return self._regex

    def expression(self):
        return self._expression

    def macros(self):
        return self._macros

    def set_macros(self, macros):
        self._macros = macros

    def __add__(self, other):
        if isinstance(other, str):
            return NatexNLU("[!" + self._expression + ", " + other + "]", macros=self._macros)
        elif isinstance(other, NatexNLU):
            return NatexNLU(
                "[!" + self._expression + ", " + other._expression + "]",
                macros=self._macros,
            )
        return self

    def __radd__(self, other):
        if isinstance(other, str):
            return NatexNLU("[!" + other + ", " + self._expression + "]", macros=self._macros)
        elif isinstance(other, NatexNLU):
            return NatexNLU(
                "[!" + other._expression + ", " + self._expression + "]",
                macros=self._macros,
            )
        return self

    def __str__(self):
        return "NatexNLU({})".format(self._expression)

    def __repr__(self):
        return str(self)

    class Compiler(Visitor):
        grammar = r"""
        start: term (","? " "? term)*
        term: flexible_sequence | rigid_sequence | conjunction | disjunction | optional | negation 
              | kleene_star | kleene_plus | regex | reference | assignment | macro | literal
        flexible_sequence: "[" " "? term (","? " "? term)* "]"
        rigid_sequence: "[!" " "? term (","? " "? term)* "]"
        conjunction: "<" term (","? " "? term)* ">"
        disjunction: "{" term (","? " "? term)* "}"
        optional: term "?"
        kleene_star: term "*"
        kleene_plus: term "+"
        negation: "-" term
        regex: "/" regex_value "/"
        reference: "$" symbol
        assignment: "$" symbol "=" term
        macro: "#" symbol ( "(" macro_arg? (","? " "? macro_arg)* ")" )? 
        macro_arg: macro_arg_string | macro_literal | macro
        macro_literal: /[^#), `][^#),`]*/
        macro_arg_string: "`" /[^`]+/ "`"
        literal: /[a-z_A-Z@.0-9:]+( +[a-z_A-Z@.0-9:]+)*/ | "\"" /[^\"]+/ "\"" | "`" /[^`]+/ "`"
        symbol: /[a-z_A-Z.0-9]+/
        regex_value: /[^\/]+/
        """
        parser = Lark(grammar, parser="earley")

        def __init__(self, natex):
            self._natex = natex
            self._parsed_tree = None
            self._tree = deepcopy(self._parsed_tree)
            self._ngrams = None
            self._vars = None
            self._macros = None
            self._assignments = set()
            self._debugging = False

        def parse(self):
            try:
                self._parsed_tree = self.parser.parse(self._natex)
            except Exception as e:
                print("Error parsing {}".format(self._natex))
                raise e

        def compile(self, ngrams, vars, macros, debugging=False):
            if self._parsed_tree is None:
                self.parse()
            self._tree = deepcopy(self._parsed_tree)
            self._assignments = set()
            self._ngrams = ngrams
            self._vars = vars
            self._macros = macros
            self._debugging = debugging
            re = self.visit(self._tree).children[0]
            self._tree = None
            self._ngrams = None
            self._vars = None
            self._macros = None
            self._assignments = set()
            if self._debugging:
                print("  {:15} {}".format("Final", re))
            return re

        def to_strings(self, args):
            strings = []
            for arg in args:
                if isinstance(arg, str):
                    strings.append(arg)
                elif isinstance(arg, set):
                    if arg:
                        strings.append(r"(?:\b" + r"\b|\b".join(arg) + r"\b)")
                    else:
                        strings.append(r"_EMPTY_SET_")
                elif isinstance(arg, bool):
                    if arg:
                        strings.append(".*")
                    else:
                        strings.append("_FALSE_")
                elif arg is None:
                    strings.append("")
            return strings

        def flexible_sequence(self, tree):
            args = [x.children[0] for x in tree.children]
            tree.data = "compiled"
            tree.children[0] = r".*?\b" + r"\b.*?\b".join(self.to_strings(args)) + r"\b.*?\b"
            if self._debugging:
                print("    {:15} {}".format("Flex. sequence", self._current_compilation(self._tree)))

        def rigid_sequence(self, tree):
            args = [x.children[0] for x in tree.children]
            tree.data = "compiled"
            tree.children[0] = r"\b" + r"\b\W*\b".join(self.to_strings(args)) + r"\b"
            if self._debugging:
                print("    {:15} {}".format("Rigid sequence", self._current_compilation(self._tree)))

        def conjunction(self, tree):
            args = [x.children[0] for x in tree.children]
            tree.data = "compiled"
            tree.children[0] = ".*?".join([r"(?=.*?\b{}\b)".format(x) for x in self.to_strings(args)]) + ".*?"
            if self._debugging:
                print("    {:15} {}".format("Conjunction", self._current_compilation(self._tree)))

        def disjunction(self, tree):
            args = [x.children[0] for x in tree.children]
            tree.data = "compiled"
            tree.children[0] = r"(?:\b{}\b)".format(r"\b|\b".join([r"(?:{})".format(x) for x in self.to_strings(args)]))
            if self._debugging:
                print("    {:15} {}".format("Disjunction", self._current_compilation(self._tree)))

        def optional(self, tree):
            args = [x.children[0] for x in tree.children]
            tree.data = "compiled"
            tree.children[0] = r"(?:\b{}\b)?".format(self.to_strings(args)[0])
            if self._debugging:
                print("    {:15} {}".format("Optional", self._current_compilation(self._tree)))

        def kleene_star(self, tree):
            args = [x.children[0] for x in tree.children]
            tree.data = "compiled"
            tree.children[0] = r"(?:\b{}\b)?(?:\b\W*{}\b)*".format(self.to_strings(args)[0], self.to_strings(args)[0])
            if self._debugging:
                print("    {:15} {}".format("Kleene *", self._current_compilation(self._tree)))

        def kleene_plus(self, tree):
            args = [x.children[0] for x in tree.children]
            tree.data = "compiled"
            tree.children[0] = r"(?:\b{}\b)(?:\b\W*{}\b)*".format(self.to_strings(args)[0], self.to_strings(args)[0])
            if self._debugging:
                print("    {:15} {}".format("Kleene +", self._current_compilation(self._tree)))

        def negation(self, tree):
            args = [x.children[0] for x in tree.children]
            tree.data = "compiled"
            (arg,) = self.to_strings(args)
            tree.children[0] = r"(?!.*\b{}\b.*)".format(arg) + ".*?"
            if self._debugging:
                print("    {:15} {}".format("Negation", self._current_compilation(self._tree)))

        def regex(self, tree):
            args = [x.children[0] for x in tree.children]
            tree.data = "compiled"
            (arg,) = self.to_strings(args)
            tree.children[0] = arg
            if self._debugging:
                print("    {:15} {}".format("Regex", self._current_compilation(self._tree)))

        def reference(self, tree):
            args = [x.children[0] for x in tree.children]
            tree.data = "compiled"
            symbol = args[0]
            if symbol in self._assignments:
                value = "(?P={})".format(symbol)
            elif symbol in self._vars:
                value = self._vars[symbol]
            else:
                value = None
            if value == "None":
                value = None
            tree.children[0] = value
            if self._debugging:
                print("    {:15} {}".format("Var reference", self._current_compilation(self._tree)))

        def assignment(self, tree):
            args = [x.children[0] for x in tree.children]
            tree.data = "compiled"
            self._assignments.add(args[0])
            value = self.to_strings([args[1]])[0]
            tree.children[0] = "(?P<{}>{})".format(args[0], value)
            if self._debugging:
                print("    {:15} {}".format("Assignment", self._current_compilation(self._tree)))

        def macro(self, tree):
            args = [x.children[0] for x in tree.children]
            tree.data = "compiled"
            symbol = args[0]
            macro_args = args[1:]
            for i in range(len(macro_args)):
                if isinstance(macro_args[i], Token):
                    macro_args[i] = str(macro_args[i])
            if symbol in self._macros:
                macro = self._macros[symbol]
                try:
                    tree.children[0] = macro(self._ngrams, self._vars, macro_args)
                except Exception as e:
                    print("ERROR: Macro {} raised exception {}".format(symbol, repr(e)))
                    traceback.print_exc(file=sys.stdout)
                    tree.children[0] = "_MACRO_EXCEPTION_"
                if self._debugging:
                    print("    {:15} {}".format(symbol, self._current_compilation(self._tree)))
            else:
                print("ERROR: Macro {} not found".format(symbol))
                tree.children[0] = "_MACRO_NOT_FOUND_"

        def macro_arg(self, tree):
            tree.children[0] = tree.children[0].children[0]
            tree.data = "compiled"

        def macro_literal(self, tree):
            tree.data = "compiled"

        def literal(self, tree):
            args = tree.children
            tree.data = "compiled"
            (literal,) = args
            tree.children[0] = literal

        def symbol(self, tree):
            args = tree.children
            tree.data = "compiled"
            (symbol,) = args
            tree.children[0] = symbol

        def term(self, tree):
            args = [x.children[0] for x in tree.children]
            tree.data = "compiled"
            (term,) = args
            tree.children[0] = term

        def start(self, tree):
            args = [x.children[0] for x in tree.children]
            tree.data = "compiled"
            tree.children[0] = r"\b\W*\b".join(self.to_strings(args)) + " _END_"

        def _current_compilation(self, tree):
            class DisplayTransformer(Transformer):
                def flexible_sequence(self, args):
                    return "[" + ", ".join([str(arg) for arg in args]) + "]"

                def rigid_sequence(self, args):
                    return "[!" + ", ".join([str(arg) for arg in args]) + "]"

                def conjunction(self, args):
                    return "<" + ", ".join([str(arg) for arg in args]) + ">"

                def disjunction(self, args):
                    return "{" + ", ".join([str(arg) for arg in args]) + "}"

                def optional(self, args):
                    return args[0] + "?"

                def kleene_star(self, args):
                    return args[0] + "*"

                def kleene_plus(self, args):
                    return args[0] + "+"

                def negation(self, args):
                    (arg,) = args
                    return "-" + str(arg)

                def regex(self, args):
                    (arg,) = args
                    return str(arg)

                def reference(self, args):
                    return "$" + args[0]

                def assignment(self, args):
                    return "${}={}".format(*args)

                def macro(self, args):
                    return "#" + args[0] + "(" + ", ".join([str(arg) for arg in args[1:]]) + ")"

                def literal(self, args):
                    return str(args[0])

                def macro_arg(self, args):
                    return str(args[0])

                def macro_literal(self, args):
                    return str(args[0])

                def symbol(self, args):
                    return str(args[0])

                def term(self, args):
                    return str(args[0])

                def start(self, args):
                    return str(args[0])

                def compiled(self, args):
                    return str(args[0])

            if not isinstance(tree, Tree):
                return str(tree)
            else:
                return DisplayTransformer().transform(tree)
