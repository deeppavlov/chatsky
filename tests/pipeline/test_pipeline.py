import sys
import importlib
import pathlib

import pytest


def test_pretty_format():
    module = importlib.import_module(f"tests.pipeline.examples.5_asynchronous_groups_and_services_full")
    module.pipeline.pretty_format()
