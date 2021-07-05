from enum import Enum, auto
import sys
import traceback
from collections import defaultdict

# from dff.state_transition_dialogue_manager.memory import Memory
from dff.state_transition_dialogue_manager.natex_nlu import NatexNLU
from dff.state_transition_dialogue_manager.natex_nlg import NatexNLG
from dff.state_transition_dialogue_manager.database import GraphDatabase
from structpy.graph.labeled_digraph import MapMultidigraph
from typing import Union, List, Dict  # , Callable, Set, Tuple, NoReturn

# from dff.state_transition_dialogue_manager.utilities import AlterationTrackingDict
from dff.state_transition_dialogue_manager.ngrams import Ngrams
from dff.state_transition_dialogue_manager.settings import Settings

# from dff.state_transition_dialogue_manager.stochastic_options import StochasticOptions
from dff.state_transition_dialogue_manager.utilities import HashableDict
from dff.state_transition_dialogue_manager.macro import Macro
from dff.state_transition_dialogue_manager.knowledge_base import KnowledgeBase

# from dff.state_transition_dialogue_manager.macros_common import *
# from dff.state_transition_dialogue_manager.natex_common import natex_macros_common
from dff.state_transition_dialogue_manager.state import State
from dff.state_transition_dialogue_manager.update_rules import UpdateRules
from dff.state_transition_dialogue_manager.utilities import random_max, get_rmapping
from dff.state_transition_dialogue_manager.utilities import (
    json_serialize_flexible,
    json_deserialize_flexible,
)
from time import time

# import dill
# from pathos.multiprocessing import ProcessingPool as Pool


def module_source_target(source, target):
    if isinstance(source, str) and ":" in source:
        i = source.find(":")
        source = (source[:i], source[i + 1 :])
    if isinstance(target, str) and ":" in target:
        i = target.find(":")
        target = (target[:i], target[i + 1 :])
    return source, target


def module_state(state):
    if isinstance(state, str) and ":" in state:
        i = state.find(":")
        state = (state[:i], state[i + 1 :])
    return state


def precache(transition_datas):
    for tran_datas in transition_datas:
        tran_datas["natex"].precache()
    parsed_trees = [x["natex"]._compiler._parsed_tree for x in transition_datas]
    return parsed_trees


_autostate = "-1"


class EnumByName(Enum):
    def _generate_next_value_(name, start, count, last_values):
        return name


class Speaker(EnumByName):
    SYSTEM = auto()
    USER = auto()


speaker_enum_mapping = {Speaker.SYSTEM: "speaker_system", Speaker.USER: "speaker_user"}
speaker_enum_rmapping = get_rmapping(speaker_enum_mapping)


class DialogueFlow:

    Speaker = Speaker

    @classmethod
    def autostate(cls):
        global _autostate
        _autostate = str(int(_autostate) + 1)
        return _autostate

    def __init__(
        self,
        initial_state: Union[Enum, str, tuple],
        initial_speaker=Speaker.SYSTEM,
        macros: Dict[str, Macro] = None,
        kb: Union[str, List[str]] = None,
        default_system_state=None,
        end_state="__end__",
        all_multi_hop=True,
        wordnet=False,
    ):
        self._graph = GraphDatabase()
        self._initial_state = State(initial_state)
        self._potential_transition = None
        self._initial_speaker = initial_speaker
        self._speaker = self._initial_speaker
        self._vars = HashableDict()
        self._transitions = []
        self._update_transitions = []
        self.vars()["__state__"] = self._initial_state
        self.set_state(self._initial_state)
        self._gates = defaultdict(list)
        self._prepends = {}
        self._var_dependencies = defaultdict(set)
        self._error_transitioned = False
        self._default_state = default_system_state
        self._end_state = end_state
        self._goals = {}
        self._all_multi_hop = all_multi_hop
        self._composite_dialogue_flow = None
        self._namespace = None
        self.vars()["__stack__"] = []
        self.vars()["__system_state__"] = "None" if initial_speaker == Speaker.USER else self._initial_state
        if kb is None:
            self._kb = KnowledgeBase()
        elif isinstance(kb, str):
            self._kb = KnowledgeBase()
            self._kb.load_json_file(kb)
        elif isinstance(kb, list):
            self._kb = KnowledgeBase()
            for filename in kb:
                self._kb.load_json_file(filename)
        else:
            self._kb = kb
        # onte = ONTE(self._kb)
        # kbe = KBE(self._kb)
        # goal_exit_macro = GoalExit(self)
        self._macros = {
            # 'WN': WN(wordnet),
            # 'ONT': onte, 'ONTE': onte,
            # 'ONTUL': ONTUL(self._kb),
            # 'KBQ': kbe, 'KBE': kbe,
            # 'ONTN': ONTN(self._kb),
            # 'EXP': EXP(self._kb),
            # 'ONT_NEG': ONT_NEG(self._kb),
            # 'FPP': FirstPersonPronoun(self._kb),
            # 'TPP': ThirdPersonPronoun(self._kb),
            # 'PSP': PossessivePronoun(self._kb),
            # 'GATE': Gate(self),
            # 'TRANSITION': Transition(self),
            # 'GOAL': GoalPursuit(goal_exit_macro, self),
            # 'GCOM': GoalCompletion(self),
            # 'GEXT': goal_exit_macro,
            # 'GSRET': SetGoalReturnPoint(),
            # 'GRET': GoalReturn(self),
            # 'GCLR': ClearGoalStack(),
            # 'VT': VirtualTransitions(self),
            # 'CE': CanEnter(self),
            # 'EXTR': ExtractList(self._kb)
        }
        # self._macros.update(macros_common_dict)
        # self._macros.update(natex_macros_common)
        if macros:
            self._macros.update(macros)
        self._rules = UpdateRules(vars=self._vars, macros=self._macros)
        self.add_state(end_state)
        self._vars["__user_utterance__"] = None

    # TOP LEVEL: SYSTEM-LEVEL USE CASES

    def run(self, debugging=False):
        """
        test in interactive mode
        :return: None
        """
        t1 = time()
        while self.state() != self.end_state():
            if self.speaker() == Speaker.SYSTEM:
                system_response = self.system_turn(debugging=debugging)
                if debugging:
                    print("Time delta: {:.5f}".format(time() - t1))
                print("S:", system_response)
            else:
                user_input = input("U: ")
                t1 = time()
                self.user_turn(user_input, debugging=debugging)

    def system_turn(self, debugging=False):
        """
        an entire system turn comprising a single system utterance and
        one or more system transitions
        :return: the natural language system response
        """
        t1 = time()
        self.vars()["__goal_return_state__"] = "None"
        visited = {self.state()}
        responses = []
        while self.speaker() is Speaker.SYSTEM:
            response, next_state = self.system_transition(self.state(), debugging=debugging)
            self.set_state(next_state)
            responses.append(response)
            if next_state in visited or (not self.state_settings(next_state).system_multi_hop):
                self.set_speaker(Speaker.USER)
            visited.add(next_state)
        t2 = time()
        if debugging:
            print("System turn in {:.5f}".format(t2 - t1))
        full_response = " ".join(responses)
        self.vars()["__selected_response__"] = full_response
        return full_response

    def user_turn(self, natural_language, debugging=False):
        """
        an entire user turn comprising one user utterance and
        one or more user transitions
        :param natural_language:
        :param debugging:
        :return: None
        """
        t1 = time()
        natural_language = "".join([c.lower() for c in natural_language if c.isalpha() or c == " "])
        self.vars()["__user_utterance__"] = natural_language
        self._transitions.clear()
        self.apply_update_rules(natural_language, debugging)
        visited = {self.state()}
        while self.speaker() is Speaker.USER:
            next_state = self.user_transition(natural_language, self.state(), debugging=debugging)
            if self._error_transitioned and next_state != self.state():
                try:
                    nns = self.user_transition(natural_language, next_state, debugging=debugging)
                    if nns not in visited:
                        next_state = nns
                except RuntimeError:
                    if debugging:
                        print("Couldn't error hop")
            self.set_state(next_state)
            if next_state in visited or (not self.state_settings(next_state).user_multi_hop):
                self.set_speaker(Speaker.SYSTEM)
            visited.add(next_state)
        self.set_speaker(Speaker.SYSTEM)
        t2 = time()
        if debugging:
            print("User turn in {:.5f}".format(t2 - t1))

    def load_transitions(self, json_dict, speaker=None):
        """
        wheeeeeeee!
        """
        if speaker is None:
            speaker = self._initial_speaker
        if "state" in json_dict:
            source = json_dict["state"]
        else:
            source = DialogueFlow.autostate()

        hop = None
        switch = False
        enter = None

        # read settings and transitions for state
        transitions = []
        for key, value in json_dict.items():
            if key == "transitions":
                assert isinstance(value, list)
                transitions = value
            elif key == "root":
                # root = json_dict["root"]
                pass
            elif key == "hop":
                hop = json_dict["hop"]
            elif key == "prepend":
                prepend = json_dict["prepend"]
                self.set_state_prepend(source, prepend)
            elif key == "switch":
                switch = json_dict["switch"]
            elif key == "enter":
                enter = json_dict["enter"]
            elif key not in {"state", "hop", "score", "switch", "enter"}:
                transitions.append((key, value))

        # set up state settings
        if not self.has_state(source):
            self.add_state(source)
        if hop:
            if speaker == Speaker.USER:
                speaker = Speaker.SYSTEM
                self.state_settings(source).update(system_multi_hop=True)
            elif speaker == Speaker.SYSTEM:
                speaker = Speaker.USER
                self.state_settings(source).update(user_multi_hop=True)
        if switch:
            self.update_state_settings(source, switch=True)
        if enter:
            self.update_state_settings(source, enter=enter)

        # set up transitions
        expanded_transitions = []
        for natex, target in transitions:
            natex_with_leading_digits_stripped = ""
            i = 0
            c = natex[i] if natex else ""
            while c and c.isnumeric():
                natex_with_leading_digits_stripped += c
                i += 1
                c = natex[i] if i < len(natex) else ""
            if natex == "error":
                if isinstance(target, dict):
                    if "state" not in target:
                        target["state"] = DialogueFlow.autostate()
                    expanded_transitions.append(target)
                    target = target["state"]
                    if not self.has_state(target):
                        self.add_state(target)
                self.set_error_successor(source, target)

            else:
                score = 1.0
                if isinstance(target, dict):
                    if "state" not in target:
                        target["state"] = DialogueFlow.autostate()
                    if "score" in target:
                        score = target["score"]
                    expanded_transitions.append(target)
                    target = target["state"]
                    if not self.has_state(target):
                        self.add_state(target)
                if speaker == Speaker.USER:
                    if self.has_transition(source, target, Speaker.USER):
                        intermediate = "_" + self.autostate()
                        self.add_state(intermediate, target)
                        self.add_user_transition(
                            source,
                            intermediate,
                            natex + " #TARGET(%s)" % target,
                            score=score,
                        )
                    else:
                        self.add_user_transition(source, target, natex, score=score)
                elif speaker == Speaker.SYSTEM:
                    if self.has_transition(source, target, Speaker.SYSTEM):
                        intermediate = "_" + self.autostate()
                        self.add_state(intermediate)
                        self.add_system_transition(
                            source,
                            intermediate,
                            natex + " #TARGET(%s)" % target,
                            score=score,
                        )
                    else:
                        self.add_system_transition(source, target, natex, score=score)

        # switch turn (will be switched back if multi hop detected on next recursive call)
        if speaker == Speaker.USER:
            speaker = Speaker.SYSTEM
        elif speaker == Speaker.SYSTEM:
            speaker = Speaker.USER

        # recurse to load nested turns
        for transition in expanded_transitions:
            self.load_transitions(transition, speaker)

    # HIGH LEVEL

    def system_transition(self, state: Union[Enum, str, tuple], debugging=False):
        """
        :param state:
        :param debugging:
        :return: a <state, response> tuple representing the successor state and response
        """
        if "__gate__" in self._vars:
            del self._vars["__gate__"]
        state = module_state(state)
        ti = time()
        if state is None:
            state = self.state()
        else:
            state = State(state)
        transition_options = []
        transitions = list(self.transitions(state, Speaker.SYSTEM))
        transition_items = []
        for transition in transitions:
            natex = self.transition_natex(*transition)
            score = self.transition_settings(*transition).score
            transition_items.append((natex, transition, score))
        while self._transitions:
            natex, transition, score = self._transitions.pop()
            transition_items.append((natex, transition, score))
        while self._update_transitions:
            natex, transition, score = self._update_transitions.pop()
            transition_items.append((natex, transition, score))
        for natex, transition, score in transition_items:
            t1 = time()
            transition_transition_enter = None
            vars = HashableDict(self._vars)
            self._potential_transition = transition  # MOVED, todo
            try:
                generation = natex.generate(vars=vars, macros=self._macros, debugging=debugging)
            except Exception as e:
                print()
                print(e)
                print("Transition {}: {} failed".format(str(transition), natex))
                traceback.print_exc(file=sys.stdout)
                print()
                generation = None
            source, target, speaker = transition
            if "__source__" in vars:
                source = State(module_state(vars["__source__"]))
                del vars["__source__"]
            if "__target__" in vars:
                target = State(module_state(vars["__target__"]))
                del vars["__target__"]
            transition = source, target, speaker
            # if not self.is_module() and isinstance(target, tuple):
            #     continue
            if "->" in transition[1]:
                _src, _tar = target.split("->")[0], target.split("->")[1]
                _tar = State(module_state(_tar))
                transition = (_src, _tar, speaker)
                try:
                    appended_generation = self.transition_natex(*transition).generate(
                        vars=vars, macros=self._macros, debugging=debugging
                    )
                    if appended_generation is None:
                        generation = None
                    else:
                        generation = generation + " " + appended_generation
                except Exception as e:
                    print()
                    print(e)
                    print("Transition {}: {} failed".format(str(transition), natex))
                    traceback.print_exc(file=sys.stdout)
                    print()
                    generation = None
            elif isinstance(transition[1], tuple) and "->" in transition[1][1]:
                namespace = transition[1][0]
                source, target = (namespace, target[1].split("->")[0]), target[1].split("->")[1]
                target = State(module_state(target))
                transition_transition_enter = source
                transition = (source, target, speaker)
                try:
                    appended_generation = (
                        self.composite_dialogue_flow()
                        .transition_natex(namespace, *transition)
                        .generate(vars=vars, macros=self._macros, debugging=debugging)
                    )
                    if generation is None or appended_generation is None:
                        generation = None
                    else:
                        generation = generation + " " + appended_generation
                except Exception as e:
                    print()
                    print(e)
                    print("Transition {}: {} failed".format(str(transition), natex))
                    traceback.print_exc(file=sys.stdout)
                    print()
                    generation = None
            source, target, speaker = transition
            if "__source__" in vars:
                source = State(module_state(vars["__source__"]))
                del vars["__source__"]
            if "__target__" in vars:
                target = State(module_state(vars["__target__"]))
                del vars["__target__"]
            transition = source, target, speaker
            enter_natex_pass = True
            transition_transition_enter_vars = vars
            if transition_transition_enter is not None:
                if self.is_module() and isinstance(transition_transition_enter, tuple):
                    enter_natex = self.composite_dialogue_flow().state_settings(*transition_transition_enter).enter
                else:
                    enter_natex = self.state_settings(transition_transition_enter).enter
                if enter_natex is not None:
                    try:
                        enter_natex_pass = enter_natex.generate(
                            vars=transition_transition_enter_vars,
                            macros=self._macros,
                            debugging=debugging,
                        )
                    except Exception as e:
                        print()
                        print(e)
                        print("Enter Natex {}: {} failed".format(str(transition_transition_enter), enter_natex))
                        print()
                        enter_natex_pass = None
            if enter_natex_pass:
                if self.is_module() and isinstance(target, tuple):
                    enter_natex = self.composite_dialogue_flow().state_settings(*target).enter
                else:
                    enter_natex = self.state_settings(target).enter
                if enter_natex is not None:
                    try:
                        enter_natex_pass = enter_natex.generate(vars=vars, macros=self._macros, debugging=debugging)
                    except Exception as e:
                        print()
                        print(e)
                        print("Enter Natex {}: {} failed".format(str(target), enter_natex))
                        print()
                        enter_natex_pass = None
            if generation is not None and enter_natex_pass is not None:
                if "__score__" in vars:
                    score = vars["__score__"]
                    del vars["__score__"]
                gate_closed = False
                gate_var_config = None
                gate_target_id = None
                if "__gate__" in vars:
                    gate_var_config = vars["__gate__"]
                    gate_target_id = (
                        (self.namespace(), target) if (not isinstance(target, tuple) and self.is_module()) else target
                    )
                    for vc in self.gates()[gate_target_id]:
                        if gate_var_config == vc:
                            gate_closed = True
                    del vars["__gate__"]
                tt_gate_var_config = None
                tt_gate_target_id = None
                if transition_transition_enter is not None and "__gate__" in transition_transition_enter_vars:
                    tt_gate_var_config = transition_transition_enter_vars["__gate__"]
                    tt_gate_target_id = (
                        (self.namespace(), transition_transition_enter)
                        if (not isinstance(transition_transition_enter, tuple) and self.is_module())
                        else transition_transition_enter
                    )
                    for vc in self.gates()[tt_gate_target_id]:
                        if tt_gate_var_config == vc:
                            gate_closed = True
                    del transition_transition_enter_vars["__gate__"]
                transition_transition_enter_vars.update(vars)
                vars = transition_transition_enter_vars
                if not gate_closed:
                    transition_options.append(
                        (
                            score,
                            natex,
                            generation,
                            transition,
                            vars,
                            gate_var_config,
                            gate_target_id,
                            tt_gate_var_config,
                            tt_gate_target_id,
                        )
                    )
            t2 = time()
            if debugging:
                print("Transition {} evaluated in {:.5f}".format(transition, t2 - t1))
            while self._transitions:
                natex, transition, score = self._transitions.pop()
                transition_items.append((natex, transition, score))
        self._transitions.clear()
        if transition_options:
            if debugging:
                print("Transition options: ------------")
                for option in transition_options:
                    print("{} {}: {}".format(option[0], option[3][1], option[1]))
                print("--------------------------------")
            (
                score,
                natex,
                response,
                transition,
                vars,
                gate_var_config,
                gate_target_id,
                tt_gate_var_config,
                tt_gate_target_id,
            ) = random_max(transition_options, key=lambda x: x[0])
            if gate_var_config is not None:
                self.gates()[gate_target_id].append(gate_var_config)
            if tt_gate_var_config is not None:
                self.gates()[tt_gate_target_id].append(tt_gate_var_config)
            if debugging:
                updates = {}
                for k, v in vars.items():
                    if k not in self._vars or v != self._vars[k]:
                        updates[k] = v
                if updates:
                    print("Updating vars:")
                    for k, v in updates.items():
                        if k in self._vars:
                            print("  {} = {} -> {}".format(k, self._vars[k], v))
                        else:
                            print("  {} = None -> {}".format(k, v))
            self.update_vars(vars)
            next_state = transition[1]
            if debugging:
                tf = time()
                print("System transition in {:.5f}".format(tf - ti))
                print("Transitioning {} -> {}".format(self.state(), next_state))
            if "__response_prefix__" in self.vars() and self.vars()["__response_prefix__"] != "None":
                response = self.vars()["__response_prefix__"] + " " + response
                self.vars()["__response_prefix__"] = "None"
            return response, next_state
        else:
            if self._default_state is not None:
                self.set_state(self._default_state)
                if debugging:
                    print("No valid system transitions found, going to default state...")
                return self.system_transition(self.state(), debugging=debugging)
            raise AssertionError("dialogue flow system transition found no valid options from state {}".format(state))

    def user_transition(self, natural_language: str, state: Union[Enum, str, tuple], debugging=False):
        """
        :param state:
        :param natural_language:
        :param debugging:
        :return: the successor state representing the highest score user transition
                 that matches natural_language, or None if none match
        """
        if "__gate__" in self._vars:
            del self._vars["__gate__"]
        if "__user_utterance__" in self.vars() and self.vars()["__user_utterance__"] is not None:
            natural_language = self.vars()["__user_utterance__"]
        else:
            natural_language = "".join([c.lower() for c in natural_language if c.isalpha() or c == " "])
        state = module_state(state)
        self._error_transitioned = False
        ti = time()
        if state is None:
            state = self.state()
        else:
            state = State(state)
        transition_options = []
        transition_items = []
        for transition in self.transitions(state, Speaker.USER):
            natex = self.transition_natex(*transition)
            score = self.transition_settings(*transition).score
            transition_items.append((natex, transition, score))
        while self._transitions:
            natex, transition, score = self._transitions.pop()
            transition_items.append((natex, transition, score))
        ngrams = Ngrams(natural_language, n=10)
        for natex, transition, score in transition_items:
            self._potential_transition = transition
            if not self.is_module() and isinstance(transition[1], tuple):
                continue
            t1 = time()
            if debugging:
                print("Evaluating transition {}".format(transition[:2]))
            vars = HashableDict(self._vars)
            try:
                match = natex.match(natural_language, vars, self._macros, ngrams, debugging)
            except Exception as e:
                print()
                print(e)
                print("Transition {}: {} failed".format(str(transition), natex))
                traceback.print_exc(file=sys.stdout)
                print()
                match = None
            source, target, speaker = transition
            if "__source__" in vars:
                source = State(module_state(vars["__source__"]))
                del vars["__source__"]
            if "__target__" in vars:
                target = State(module_state(vars["__target__"]))
                del vars["__target__"]
            transition = source, target, speaker
            if self.is_module() and isinstance(target, tuple):
                enter_natex = self.composite_dialogue_flow().state_settings(*target).enter
            else:
                enter_natex = self.state_settings(target).enter
            enter_natex_pass = True
            if enter_natex is not None:
                try:
                    enter_natex_pass = enter_natex.generate(vars=vars, macros=self._macros, debugging=debugging)
                except Exception as e:
                    print()
                    print(e)
                    print("Enter Natex {}: {} failed".format(str(target), enter_natex))
                    print()
                    enter_natex_pass = None
            if match and enter_natex_pass is not None:
                if debugging:
                    print('Transition {} matched "{}"'.format(transition[:2], natural_language))
                if "__score__" in vars:
                    score = vars["__score__"]
                    del vars["__score__"]
                gate_closed = False
                gate_var_config = None
                gate_target_id = None
                if "__gate__" in vars:
                    gate_var_config = vars["__gate__"]
                    gate_target_id = (
                        (self.namespace(), target) if (not isinstance(target, tuple) and self.is_module()) else target
                    )
                    for vc in self.gates()[gate_target_id]:
                        if gate_var_config == vc:
                            gate_closed = True
                    del vars["__gate__"]
                if not gate_closed:
                    transition_options.append(
                        (
                            score,
                            natex,
                            transition,
                            vars,
                            gate_var_config,
                            gate_target_id,
                        )
                    )
            t2 = time()
            if debugging:
                print("Transition {} evaluated in {:.5f}".format(transition, t2 - t1))
            while self._transitions:
                natex, transition, score = self._transitions.pop()
                transition_items.append((natex, transition, score))
        self._transitions.clear()
        if transition_options:
            if debugging:
                print("Transition options: ------------")
                for option in transition_options:
                    print("{} {}: {}".format(option[0], option[2][1], option[1]))
                print("--------------------------------")
            (
                score,
                natex,
                transition,
                vars,
                gate_var_config,
                gate_target_id,
            ) = random_max(transition_options, key=lambda x: x[0])
            if gate_var_config is not None:
                self.gates()[gate_target_id].append(gate_var_config)
            if debugging:
                updates = {}
                for k, v in vars.items():
                    if k not in self._vars or v != self._vars[k]:
                        updates[k] = v
                if updates:
                    print("Updating vars:")
                    for k, v in updates.items():
                        if k in self._vars:
                            print("  {} = {} -> {}".format(k, self._vars[k], v))
                        else:
                            print("  {} = None -> {}".format(k, v))
            self.update_vars(vars)
            next_state = transition[1]
            if debugging:
                print("User transition in {:.5f}".format(time() - ti))
                print("Transitioning {} -> {}".format(self.state(), next_state))
            return next_state
        else:
            self._error_transitioned = True
            next_state = self.error_successor(self.state())
            if debugging:
                print("User transition in {:.5f}".format(time() - ti))
                print("Error transition {} -> {}".format(self.state(), next_state))
            return next_state

    def precache_transitions(self, process_num=1):
        """
        Make DialogueFlow fast from the start with the power of precache!
        """
        if process_num == 1:
            for transition in self._graph.arcs():
                data = self._graph.arc_data(*transition)
                data["natex"].precache()
            for rule in self.update_rules().rules:
                rule.precondition.precache()
                if rule.postcondition:
                    rule.postcondition.precache()
        else:
            # transition_data_sets = []
            # for i in range(process_num):
            #     transition_data_sets.append([])
            # count = 0
            # for transition in self._graph.arcs():
            #     transition_data_sets[count].append(self._graph.arc_data(*transition))
            #     count = (count + 1) % process_num
            #
            # print("multiprocessing...")
            # p = Pool(process_num)
            # results = p.map(precache, transition_data_sets)
            # for i in range(len(results)):
            #     result_list = results[i]
            #     t_list = transition_data_sets[i]
            #     for j in range(len(result_list)):
            #         parsed_tree = result_list[j]
            #         t = t_list[j]
            #         t['natex']._compiler._parsed_tree = parsed_tree
            raise NotImplementedError()

    def check(self, debugging=False):
        all_good = True
        for state in self._graph.nodes():
            has_system_fallback = False
            has_user_fallback = False
            for source, target, speaker in self._graph.arcs_out(state):
                if speaker == Speaker.SYSTEM:
                    if self.transition_natex(source, target, speaker).is_complete():
                        has_system_fallback = True
            if self.error_successor(state) is not None:
                has_user_fallback = True
            in_labels = {x[2] for x in self.incoming_transitions(state)}
            if Speaker.SYSTEM in in_labels:
                if not has_user_fallback:
                    if debugging:
                        print("WARNING: Turn-taking dead end: state {} has no fallback user transition".format(state))
                    all_good = False
            if Speaker.USER in in_labels:
                if not has_system_fallback:
                    if debugging:
                        print(
                            "WARNING: Turn-taking dead end: state {} may have no fallback system transitions".format(
                                state
                            )
                        )
                    all_good = False
        return all_good

    def add_user_transition(
        self,
        source: Union[Enum, str, tuple],
        target: Union[Enum, str, tuple],
        natex_nlu: Union[str, NatexNLU, List[str]],
        **settings
    ):
        source, target = module_source_target(source, target)
        source = State(source)
        target = State(target)
        if self.has_transition(source, target, Speaker.USER):
            raise ValueError("user transition {} -> {} already exists".format(source, target))
        natex_nlu = NatexNLU(natex_nlu, macros=self._macros)
        if not self.has_state(source):
            self.add_state(source)
        if not self.has_state(target):
            self.add_state(target)
        self._graph.add_arc(source, target, Speaker.USER)
        self.set_transition_natex(source, target, Speaker.USER, natex_nlu)
        transition_settings = Settings(score=1.0)
        transition_settings.update(**settings)
        if self._all_multi_hop:
            self.update_state_settings(source, user_multi_hop=True)
        self.set_transition_settings(source, target, Speaker.USER, transition_settings)
        if target in self._prepends:
            prepend = self._prepends[target]
            natex = self.transition_natex(source, target, Speaker.USER)
            self.set_transition_natex(source, target, Speaker.USER, prepend + natex)

    def add_system_transition(
        self,
        source: Union[Enum, str, tuple],
        target: Union[Enum, str, tuple],
        natex_nlg: Union[str, NatexNLG, List[str]],
        **settings
    ):
        source, target = module_source_target(source, target)
        source = State(source)
        target = State(target)
        if self.has_transition(source, target, Speaker.SYSTEM):
            raise ValueError("system transition {} -> {} already exists".format(source, target))
        natex_nlg = NatexNLG(natex_nlg, macros=self._macros)
        if not self.has_state(source):
            self.add_state(source)
        if not self.has_state(target):
            self.add_state(target)
        self._graph.add_arc(source, target, Speaker.SYSTEM)
        self.set_transition_natex(source, target, Speaker.SYSTEM, natex_nlg)
        transition_settings = Settings(score=1.0)
        transition_settings.update(**settings)
        self.set_transition_settings(source, target, Speaker.SYSTEM, transition_settings)
        if self._all_multi_hop:
            self.update_state_settings(source, system_multi_hop=True)
        if target in self._prepends:
            prepend = self._prepends[target]
            natex = self.transition_natex(source, target, Speaker.SYSTEM)
            self.set_transition_natex(source, target, Speaker.SYSTEM, prepend + natex)

    def add_state(
        self, state: Union[Enum, str, tuple], error_successor: Union[Union[Enum, str, tuple], None] = None, **settings
    ):
        state = module_state(state)
        state = State(state)
        if self.has_state(state):
            raise ValueError("state {} already exists".format(state))
        state_settings = Settings(user_multi_hop=False, system_multi_hop=False, switch=False, enter=None)
        state_settings.update(**settings)
        self._graph.add_node(state)
        self.update_state_settings(state, **state_settings)
        if error_successor is not None:
            error_successor = State(error_successor)
            self.set_error_successor(state, error_successor)

    # LOW LEVEL: PROPERTIES, GETTERS, SETTERS

    def transition_natex(
        self,
        source: Union[Enum, str, tuple],
        target: Union[Enum, str, tuple],
        speaker: Enum,
    ):
        source, target = module_source_target(source, target)
        source = State(source)
        target = State(target)
        return self._graph.arc_data(source, target, speaker)["natex"]

    def set_transition_natex(self, source, target, speaker, natex):
        source, target = module_source_target(source, target)
        source = State(source)
        target = State(target)
        if isinstance(natex, str):
            if speaker == Speaker.USER:
                natex = NatexNLU(natex, macros=self._macros)
            else:
                natex = NatexNLG(natex, macros=self._macros)
        self._graph.arc_data(source, target, speaker)["natex"] = natex

    def transition_settings(
        self,
        source: Union[Enum, str, tuple],
        target: Union[Enum, str, tuple],
        speaker: Enum,
    ):
        source, target = module_source_target(source, target)
        source = State(source)
        target = State(target)
        return self._graph.arc_data(source, target, speaker)["settings"]

    def set_transition_settings(self, source, target, speaker, settings):
        source, target = module_source_target(source, target)
        source = State(source)
        target = State(target)
        self._graph.arc_data(source, target, speaker)["settings"] = settings

    def update_transition_settings(self, source, target, speaker, **settings):
        source, target = module_source_target(source, target)
        source = State(source)
        target = State(target)
        self.transition_settings(source, target, speaker).update(**settings)

    def state_settings(self, state):
        state = module_state(state)
        state = State(state)
        return self._graph.data(state)["settings"]

    def add_global_nlu(self, state, nlu, score=0.5, post_nlu=None):
        state = module_state(state)
        state = State(state)
        if not self.has_state(state):
            self.add_state(state)
        if isinstance(state, tuple):
            state = ":".join(state)
        if isinstance(nlu, list) or isinstance(nlu, set):
            nlu = "{" + ", ".join(nlu) + "}"
        if post_nlu is None:
            self._rules.add("{} ({})".format(nlu, score), "#TRANSITION({}, {})".format(state, score))
        else:
            self._rules.add(
                "{} ({})".format(nlu, score),
                "#TRANSITION({}, {}, {})".format(state, score, post_nlu),
            )

    def update_state_settings(self, state, **settings):
        state = module_state(state)
        state = State(state)
        if "settings" not in self._graph.data(state):
            self._graph.data(state)["settings"] = Settings()
        if "global_nlu" in settings:
            self.add_global_nlu(state, settings["global_nlu"])
        if "enter" in settings and isinstance(settings["enter"], str):
            settings["enter"] = NatexNLG(settings["enter"], macros=self._macros)
        self.state_settings(state).update(**settings)

    def remove_transition(self, source, target, speaker):
        source, target = module_source_target(source, target)
        source = State(source)
        target = State(target)
        MapMultidigraph.remove_arc(self.graph(), source, target, speaker)

    def states(self):
        return self.graph().nodes()

    def state(self):
        return self._vars["__state__"]

    def set_state(self, state: Union[Enum, str, tuple]):
        state = module_state(state)
        state = State(state)
        if self.speaker() == Speaker.SYSTEM:
            if "__state__" in self.vars():
                st_str = (
                    self.vars()["__state__"][1]
                    if isinstance(self.vars()["__state__"], tuple)
                    else self.vars()["__state__"]
                )
                if not st_str.startswith("_"):
                    self.vars()["__system_state__"] = self.vars()["__state__"]
                if "__system_state__" not in self.vars():
                    self.vars()["__system_state__"] = "None"
            else:
                self.vars()["__system_state__"] = "None"
        self._vars["__state__"] = state

    def has_state(self, state):
        state = module_state(state)
        state = State(state)
        return self._graph.has_node(state)

    def error_successor(self, state):
        state = module_state(state)
        state = State(state)
        data = self._graph.data(state)
        if "error" in data:
            return data["error"]
        else:
            return None

    def set_error_successor(self, state, error_successor):
        state, error_successor = module_source_target(state, error_successor)
        state = State(state)
        error_successor = State(error_successor)
        self._graph.data(state)["error"] = error_successor

    def speaker(self):
        return self._speaker

    def set_speaker(self, speaker: Enum):
        self._speaker = speaker

    def graph(self):
        return self._graph

    def vars(self):
        return self._vars

    def set_vars(self, vars):
        self._vars = vars
        self.update_rules().set_vars(vars)

    def transitions(self, source_state, speaker=None):
        """
        get (source, target, speaker) transition tuples for the entire state machine
        (default) or that lead out from a given source_state
        :param source_state: optionally, filter returned transitions by source state
        :param speaker: optionally, filter returned transitions by speaker
        :return: a generator over (source, target, speaker) 3-tuples
        """
        source_state = module_state(source_state)
        source_state = State(source_state)
        if speaker is None:
            yield from self._graph.arcs_out(source_state)
        elif self._graph.has_arc_label(source_state, speaker):
            yield from self._graph.arcs_out(source_state, label=speaker)
        else:
            return

    def has_transition(self, source, target, speaker):
        source, target = module_source_target(source, target)
        source = State(source)
        target = State(target)
        return self._graph.has_arc(source, target, speaker)

    def incoming_transitions(self, target_state):
        target_state = module_state(target_state)
        target_state = State(target_state)
        yield from self._graph.arcs_in(target_state)

    def change_speaker(self):
        if self.speaker() is Speaker.USER:
            self.set_speaker(Speaker.SYSTEM)
        elif self.Speaker is Speaker.SYSTEM:
            self.set_speaker(Speaker.USER)

    def reset(self):
        self._transitions.clear()
        self._speaker = self._initial_speaker
        self._vars = HashableDict()
        self.vars()["__state__"] = self._initial_state
        self.vars()["__stack__"] = []
        self.vars()["__user_utterance__"] = None
        self.vars()["__system_state__"] = "None" if self._initial_speaker == Speaker.USER else self._initial_state
        self.set_state(self._initial_state)
        self._rules.set_vars(self._vars)
        self._gates = defaultdict(list)

    def update_vars(self, variables: HashableDict):
        if not isinstance(variables, HashableDict):
            variables = HashableDict(variables)
        for k in variables:
            if k in self._var_dependencies:
                dependencies = self._var_dependencies[k]
                for dependency in dependencies:
                    if dependency in self._vars:
                        self._vars[dependency] = None
        self._vars.update({k: variables[k] for k in variables if k != "__score__" and k in variables})

    def potential_transition(self):
        return self._potential_transition

    def gates(self):
        return self._gates

    def var_dependencies(self):
        return self._var_dependencies

    def set_state_prepend(self, state, prepend):
        state = module_state(state)
        self._prepends[state] = prepend
        if self.has_state(state):
            for transition in self._graph.arcs_in(state):
                natex = self.transition_natex(*transition)
                self.set_transition_natex(*transition, prepend + natex)

    def add_update_rule(self, precondition, postcondition=None):
        self._rules.add(precondition, postcondition)

    def apply_update_rules(self, user_input, debugging=False):
        result = self._rules.update(user_input, debugging)
        if result is not None:
            response, score = result
            self._update_transitions.append((response, (self.state(), self.state(), Speaker.SYSTEM), score))
            # self.set_speaker(Speaker.SYSTEM)

    def knowledge_base(self):
        return self._kb

    def set_is_module(self, composite_dialogue_flow):
        self._composite_dialogue_flow = composite_dialogue_flow

    def is_switch(self, state):
        return self.state_settings(state)["switch"]

    def end_state(self):
        return self._end_state

    def update_rules(self):
        return self._rules

    def goals(self):
        return self._goals

    def set_goals(self, goals_dict):
        self._goals = goals_dict

    def dynamic_transitions(self):
        return self._transitions

    def composite_dialogue_flow(self):
        return self._composite_dialogue_flow

    def is_module(self):
        return self.composite_dialogue_flow() is not None

    def namespace(self):
        return self._namespace

    def add_macros(self, macro_dict):
        self._macros.update(macro_dict)

    def set_namespace(self, namespace):
        self._namespace = namespace

    def set_gates(self, gates):
        self._gates = gates

    def load_global_nlu(self, transitions, default_score=0.5):
        orig_score = default_score
        for nlu, followup in transitions.items():
            default_score = orig_score
            if nlu == "state":
                continue
            if isinstance(followup, str):
                state = followup
            else:
                if "state" not in followup:
                    state = DialogueFlow.autostate()
                    followup["state"] = state
                else:
                    state = followup["state"]
                if "score" in followup:
                    default_score = followup["score"]
            self.add_global_nlu(state, nlu, default_score, post_nlu="`/.*/ #GEXT`")
        self.load_transitions(transitions, Speaker.USER)

    def load_update_rules(self, rules_dict, score=None):
        for pre, post in rules_dict.items():
            self.update_rules().add(pre, post, score=score)

    def macros(self):
        return self._macros

    def add_goal(self, id_string, return_state=None, return_phrase=None, doom_counter=None):
        goal = {
            "id": id_string,
            "return_state": return_state,
            "return_phrase": return_phrase,
            "doom_counter": doom_counter,
        }
        self._goals[id_string] = goal

    def serialize(self):
        """
        Returns json serialized dict of
            {'vars': vars, 'gates': gates, 'state': state}
        """
        config = {"vars": self.vars(), "gates": self.gates(), "state": self.state()}
        return json_serialize_flexible(config, speaker_enum_mapping)

    def deserialize(self, config_str):
        config = json_deserialize_flexible(config_str, speaker_enum_rmapping)
        self.reset()
        self.set_state(config["state"])
        self.set_vars(config["vars"])
        self.set_gates(config["gates"])
