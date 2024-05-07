from importlib import import_module
from pathlib import Path
import pytest

from tests.test_utils import get_path_from_tests_to_current_dir

dot_path_to_addon = get_path_from_tests_to_current_dir(__file__)
happy_paths_file = Path(__file__).parent / "test_happy_paths.json"    


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ["tutorial_module_name"],
    [("1_basic",), ("2_attachments",), ("3_advanced",)],
)
async def test_tutorials_memory(tutorial_module_name: str):
    module = import_module(f"tutorials.{dot_path_to_addon}.{tutorial_module_name}")
    module.interface.application
