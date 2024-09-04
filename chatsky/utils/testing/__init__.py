# -*- coding: utf-8 -*-
from .common import is_interactive_mode, check_happy_path
from .toy_script import TOY_SCRIPT, TOY_SCRIPT_KWARGS, HAPPY_PATH

try:
    import pytest

    pytest.register_assert_rewrite("chatsky.utils.testing.telegram")
except ImportError:
    ...
