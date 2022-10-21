import sys
import importlib
import pathlib

import pytest


def test_pretty_format():
    sys.path.append(str((pathlib.Path(__file__).parent / 'examples').absolute()))
    module = importlib.import_module(f"5_asynchronous_groups_and_services_full", package="examples")
    module.pipeline.pretty_format()
