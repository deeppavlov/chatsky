import sys
import importlib
import pathlib

import pytest


def test_pretty_format():
    sys.path.append(str(pathlib.Path(__file__).parent.absolute()))
    module = importlib.import_module(f"examples.5_asynchronous_groups_and_services_full")
    module.pipeline.pretty_format()
