# from importlib import import_module
# from json import loads
# from pathlib import Path
# from typing import Dict, List

# import pytest

# from dff.script.core.message import Message
# from mock_bot import MockApplication, PathStep
# from tests.test_utils import get_path_from_tests_to_current_dir

# dot_path_to_addon = get_path_from_tests_to_current_dir(__file__, separator=".")
# happy_paths_file = Path(__file__).parent / "test_tutorial.json"

# def _cast_dict_to_happy_step(dict: Dict) -> List[PathStep]:
#     imports = globals().copy()
#     # imports.update(import_module("vk_api").__dict__)

#     path_steps = list()
#     for step in dict:
#         update = step["update"]
#         received = Message.model_validate_json(step["received_message"])
#         received.original_message = update
#         response = Message.model_validate_json(step["response"])
#         path_steps += [(update, received, response, step["response_request"])]
#     return path_steps

# @pytest.mark.vk
# @pytest.mark.asyncio
# @pytest.mark.parametrize(
#     "tutorial_module_name",
#     ["1_basic"],
# )
# def test_tutorials_vk_memory(tutorial_module_name: str):
#     happy_path_data = loads(happy_paths_file.read_text())[tutorial_module_name]
#     happy_path_steps = _cast_dict_to_happy_step(happy_path_data)
#     module = import_module(f"tutorials.{dot_path_to_addon}.{tutorial_module_name}")
#     module.interface.application = MockApplication.create(module.interface, happy_path_steps)
#     module.pipeline.run()
