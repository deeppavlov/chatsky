from collections import defaultdict
import sys
from dff.state_transition_dialogue_manager.dialogue_flow import (
    DialogueFlow,
    module_source_target,
    module_state,
)

# from dff.state_transition_dialogue_manager.macros_common import *
from dff.state_transition_dialogue_manager.utilities import (
    json_serialize_flexible,
    json_deserialize_flexible,
)
from dff.state_transition_dialogue_manager.dialogue_flow import (
    speaker_enum_mapping,
    speaker_enum_rmapping,
)
from time import time

# import dill
# from pathos.multiprocessing import ProcessingPool as Pool
import traceback


def precache(transition_datas):
    for tran_datas in transition_datas:
        tran_datas["natex"].precache()
    parsed_trees = [x["natex"]._compiler._parsed_tree for x in transition_datas]
    return parsed_trees


class CompositeDialogueFlow:
    def __init__(
        self,
        initial_state,
        system_error_state,
        user_error_state,
        initial_speaker=DialogueFlow.Speaker.SYSTEM,
        macros=None,
        kb=None,
    ):
        if isinstance(system_error_state, str):
            system_error_state = ("SYSTEM", system_error_state)
        if isinstance(user_error_state, str):
            user_error_state = ("SYSTEM", user_error_state)
        # the dialogue flow currently controlling the conversation
        self._controller = DialogueFlow(initial_state, initial_speaker, macros, kb)
        self._controller_name = "SYSTEM"
        # namespace : dialogue flow mapping
        self._components = {}
        self.add_component(self._controller, "SYSTEM")
        self._system_error_state = system_error_state
        self._user_error_state = user_error_state

    def run(self, debugging=False):
        """
        test in interactive mode
        :return: None
        """
        while True:
            if self.controller().speaker() == DialogueFlow.Speaker.SYSTEM:
                t1 = time()
                response = self.system_turn(debugging=debugging)
                if debugging:
                    print("System turn in {:5}".format(time() - t1))
                print("S:", response)
            else:
                user_input = input("U: ")
                t1 = time()
                self.user_turn(user_input, debugging=debugging)
                if debugging:
                    print("User turn in {:5}".format(time() - t1))

    def system_turn(self, debugging=False):
        """
        an entire system turn comprising a single system utterance and
        one or more system transitions
        :return: the natural language system response
        """
        visited = {self._controller.state()}
        self.controller().vars()["__goal_return_state__"] = "None"
        responses = []
        while self.controller().speaker() is DialogueFlow.Speaker.SYSTEM:
            try:
                response, next_state = self.controller().system_transition(
                    self.controller().state(), debugging=debugging
                )
                assert next_state is not None
                self.controller().set_state(next_state)
            except Exception as e:
                print()
                print(e)
                print(
                    "Error in CompositeDialogueFlow. Component: {}  State: {}".format(
                        self.controller_name(), self.controller().state()
                    )
                )
                traceback.print_exc(file=sys.stdout)
                response, next_state = "", self._system_error_state
                visited = visited - {next_state}
            if isinstance(next_state, tuple):
                self.set_control(*next_state)
            responses.append(response)
            if next_state in visited or not self.state_settings(*self.state()).system_multi_hop:
                self.controller().set_speaker(DialogueFlow.Speaker.USER)
            visited.add(next_state)
        full_response = " ".join(responses)
        self.controller().vars()["__selected_response__"] = full_response
        return full_response

    def user_turn(self, natural_language, debugging=False):
        """
        an entire user turn comprising one user utterance and
        one or more user transitions
        :param natural_language:
        :param debugging:
        :return: None
        """
        self.controller().vars()["__user_utterance__"] = natural_language
        try:
            self.controller().apply_update_rules(natural_language, debugging=debugging)
            next_state = self.controller().state()
        except Exception as e:
            print()
            print(e)
            print(
                "Error in CompositeDialogueFlow. Component: {}  State: {}".format(
                    self._controller_name, self.controller().state()
                )
            )
            traceback.print_exc(file=sys.stdout)
            next_state = self._user_error_state
        visited = {self.controller().state()}
        while self.controller().speaker() is DialogueFlow.Speaker.USER:
            try:
                next_state = self.controller().user_transition(
                    natural_language, self.controller().state(), debugging=debugging
                )
                assert next_state is not None
                self.controller().set_state(next_state)
            except Exception as e:
                print()
                print(e)
                print(
                    "Error in CompositeDialogueFlow. Component: {}  State: {}".format(
                        self._controller_name, self.controller().state()
                    )
                )
                traceback.print_exc(file=sys.stdout)
                next_state = self._user_error_state
            next_state = module_state(next_state)
            if isinstance(next_state, tuple):
                self.set_control(*next_state)
                if self.state_settings(*self.state()).user_multi_hop:
                    self.controller().apply_update_rules(natural_language, debugging=debugging)
            if next_state in visited or not self.state_settings(*self.state()).user_multi_hop:
                self.controller().set_speaker(DialogueFlow.Speaker.SYSTEM)
            visited.add(next_state)
        next_state = module_state(next_state)
        if isinstance(next_state, tuple):
            self.set_control(*next_state)
            if self.controller().speaker() is DialogueFlow.Speaker.USER:
                self.controller().apply_update_rules(natural_language, debugging=debugging)

    def set_control(self, namespace, state):
        state = module_state(state)
        speaker = self.controller().speaker()
        old_state = self.controller().state()
        self.component(namespace).set_state(old_state)
        self.set_controller(namespace)
        self.controller().set_speaker(speaker)
        if isinstance(state, tuple):
            umh = self.state_settings(*state).user_multi_hop
            smh = self.state_settings(*state).system_multi_hop
        else:
            umh = self.state_settings(namespace, state).user_multi_hop
            smh = self.state_settings(namespace, state).system_multi_hop
        if speaker == DialogueFlow.Speaker.USER and not umh:
            self.controller().change_speaker()
        elif speaker == DialogueFlow.Speaker.SYSTEM and not smh:
            self.controller().change_speaker()
        self.controller().set_state(state)

    def precache_transitions(self, process_num=1):
        start = time()

        transition_data_sets = []
        for i in range(process_num):
            transition_data_sets.append([])
        # count = 0

        if process_num == 1:
            for name, df in self._components.items():
                df.precache_transitions(process_num)
        else:
            # for name,df in self._components.items():
            #     for transition in df._graph.arcs():
            #         transition_data_sets[count].append(df._graph.arc_data(*transition))
            #         count = (count + 1) % process_num
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

        print("Elapsed: ", time() - start)

    def add_state(self, state, error_successor=None):
        state = module_state(state)
        if isinstance(state, tuple):
            ns, state = state
        else:
            ns = "SYSTEM"
        self._components[ns].add_state(state, error_successor)

    def add_user_transition(self, source, target, natex_nlu, **settings):
        source, target = module_source_target(source, target)
        if isinstance(source, tuple):
            ns, source = source
        else:
            ns = "SYSTEM"
        self._components[ns].add_user_transition(source, target, natex_nlu, **settings)

    def add_system_transition(self, source, target, natex_nlg, **settings):
        source, target = module_source_target(source, target)
        if isinstance(source, tuple):
            ns, source = source
        else:
            ns = "SYSTEM"
        self._components[ns].add_system_transition(source, target, natex_nlg, **settings)

    def add_component(self, component, namespace):
        self._components[namespace] = component
        component.set_is_module(self)
        component.set_namespace(namespace)
        component.set_gates(self.component("SYSTEM").gates())

    def component(self, namespace):
        return self._components[namespace]

    def components(self):
        return self._components.values()

    def set_state(self, state):
        state = module_state(state)
        if isinstance(state, tuple):
            if self.component(state[0]) != self.controller():
                self.component(state[0]).set_state(self.controller().state())  # so __system_state__ is set properly
                self.set_controller(state[0])
            state = state[1]
        self.controller().set_state(state)

    def set_controller(self, controller_name):
        old_controller_vars = self._controller.vars()
        if self._controller_name != controller_name:
            del old_controller_vars["__state__"]
        self._controller = self.component(controller_name)
        self._controller_name = controller_name
        new_controller_vars = self._controller.vars()
        new_controller_vars.update(old_controller_vars)
        self._controller.set_vars(new_controller_vars)

    def transition_natex(self, namespace, source, target, speaker):
        source, target = module_source_target(source, target)
        if isinstance(source, tuple):
            source = source[1]
        if isinstance(target, tuple):
            target = target[1]
        return self.component(namespace).transition_natex(source, target, speaker)

    def state_settings(self, namespace, state):
        return self.component(namespace).state_settings(state)

    def set_vars(self, vars):
        self._controller.set_vars(vars)

    def reset(self):
        gates = None
        goals = None
        for name, component in self._components.items():
            component.reset()
            if gates is None:
                gates = component.gates()
                goals = component.goals()
            component.set_gates(gates)
            component.set_goals(goals)
        self.set_controller("SYSTEM")

    def controller(self):
        return self._controller

    def controller_name(self):
        return self._controller_name

    def state(self):
        return self._controller_name, self._controller.state()

    def serialize(self):
        """
        Returns json serialized dict of
            {'vars': vars, 'gates': gates, 'state': state}
        """
        config = {
            "vars": self._controller.vars(),
            "gates": self._controller.gates(),
            "state": self.state(),
        }
        return json_serialize_flexible(config, speaker_enum_mapping)

    def deserialize(self, config_str):
        config = json_deserialize_flexible(config_str, speaker_enum_rmapping)
        self.reset()
        self.set_state(config["state"])
        self.set_vars(config["vars"])
        gates = defaultdict(list, config["gates"])
        for name, component in self._components.items():
            component.set_gates(gates)

    def new_turn(self, toplevel="SYSTEM"):
        self.reset()
        self.set_controller(toplevel)
