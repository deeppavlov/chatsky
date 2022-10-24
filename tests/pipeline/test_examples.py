import os
import sys
import importlib
import pathlib

import pytest

from .examples._utils import auto_run_pipeline


# Uncomment the following line, if you want to run your examples during the test suite or import from them
# pytest.skip(allow_module_level=True)


@pytest.mark.parametrize(
    "module_name", [
        "1_basic_example",
        "2_pre_and_post_processors",
        "3_pipeline_dict_with_services_basic",
        "3_pipeline_dict_with_services_full",
        "4_groups_and_conditions_basic",
        "4_groups_and_conditions_full",
        "5_asynchronous_groups_and_services_basic",
        "5_asynchronous_groups_and_services_full",
        "6_custom_messenger_interface",
        "7_extra_handlers_basic",
        "7_extra_handlers_full",
        "8_extra_handlers_and_extensions",
    ]
)
def test_examples(module_name: str):
    module = importlib.import_module(f"tests.pipeline.examples.{module_name}")
    if module_name.startswith("6"):
        auto_run_pipeline(module.pipeline, wrapper=module.construct_webpage_by_response)
    else:
        auto_run_pipeline(module.pipeline)
