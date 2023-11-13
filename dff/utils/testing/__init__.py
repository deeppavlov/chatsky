# -*- coding: utf-8 -*-
from .common import is_interactive_mode, check_happy_path, run_interactive_mode
from .toy_script import TOY_SCRIPT, TOY_SCRIPT_ARGS, HAPPY_PATH
from .response_comparers import default_comparer

try:
    import pytest

    pytest.register_assert_rewrite("dff.utils.testing.telegram")
except ImportError:
    ...
