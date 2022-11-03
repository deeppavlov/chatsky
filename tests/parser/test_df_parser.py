"""Parser tests."""
from pathlib import Path

import pytest

from dff.script.import_export.parser.utils.convenience_functions import get_module_name
from dff.script.import_export.parser.utils.exceptions import ModuleNotFoundParserError
from dff.script.import_export.parser.utils.module_metadata import get_module_info, ModuleType


TEST_DIR = Path(__file__).parent / "TEST_CASES"


class TestSimpleFunctions:
    @pytest.mark.parametrize(
        "file,project_root_dir,answer",
        [
            (TEST_DIR / "test_directory" / "__init__.py", TEST_DIR / "test_directory", "test_directory.__init__"),
            (TEST_DIR / "test_directory" / "file.py", TEST_DIR / "test_directory", "test_directory.file"),
            (
                TEST_DIR / "test_directory" / "another_package" / "__init__.py",
                TEST_DIR / "test_directory",
                "test_directory.another_package.__init__",
            ),
            (
                TEST_DIR / "test_directory" / "another_package" / "file.py",
                TEST_DIR / "test_directory",
                "test_directory.another_package.file",
            ),
            (TEST_DIR / "test_directory" / "dir" / "file.py", TEST_DIR / "test_directory" / "dir", "file"),
        ],
    )
    def test_get_module_name(self, file, project_root_dir, answer):
        assert get_module_name(file, project_root_dir) == answer

    @pytest.mark.parametrize(
        "args,answer,exception",
        [
            (
                ("file", TEST_DIR / "test_directory"),
                (ModuleType.LOCAL, str((TEST_DIR / "test_directory" / "file.py").absolute())),
                None,
            ),
            (
                ("file", TEST_DIR / "test_directory" / "another_package"),
                (ModuleType.LOCAL, str((TEST_DIR / "test_directory" / "another_package" / "file.py").absolute())),
                None,
            ),
            (
                ("another_package", TEST_DIR / "test_directory"),
                (ModuleType.LOCAL, str((TEST_DIR / "test_directory" / "another_package" / "__init__.py").absolute())),
                None,
            ),
            (
                ("..file", TEST_DIR / "test_directory" / "another_package"),
                (ModuleType.LOCAL, str((TEST_DIR / "test_directory" / "file.py").absolute())),
                None,
            ),
            (
                ("dir.file", TEST_DIR / "test_directory"),
                (ModuleType.LOCAL, str((TEST_DIR / "test_directory" / "dir" / "file.py").absolute())),
                None,
            ),
            (
                ("dir.file_does_not_exist", TEST_DIR / "test_directory"),
                None,
                ModuleNotFoundParserError,
            ),
            (
                ("importlib.util", TEST_DIR),
                (ModuleType.SYSTEM, "importlib"),
                None,
            ),
            (
                ("importlib.submodule_does_not_exist", TEST_DIR),
                None,
                ModuleNotFoundParserError,
            ),
            (
                ("package_does_not_exist", TEST_DIR),
                None,
                ModuleNotFoundParserError,
            ),
            (
                ("..nodes", TEST_DIR / "test_py2yaml" / "complex_tests" / "test_1" / "python_files" / "flows"),
                (
                    ModuleType.LOCAL,
                    str(
                        (
                            TEST_DIR
                            / "test_py2yaml"
                            / "complex_tests"
                            / "test_1"
                            / "python_files"
                            / "nodes"
                            / "__init__.py"
                        ).absolute()
                    ),
                ),
                None,
            ),
            (
                (
                    "..nodes.fallback_node",
                    TEST_DIR / "test_py2yaml" / "complex_tests" / "test_1" / "python_files" / "flows",
                ),
                (
                    ModuleType.LOCAL,
                    str(
                        (
                            TEST_DIR
                            / "test_py2yaml"
                            / "complex_tests"
                            / "test_1"
                            / "python_files"
                            / "nodes"
                            / "fallback_node.py"
                        ).absolute()
                    ),
                ),
                None,
            ),
            (
                ("..main", TEST_DIR / "test_py2yaml" / "complex_tests" / "test_1" / "python_files" / "flows"),
                (
                    ModuleType.LOCAL,
                    str(
                        (TEST_DIR / "test_py2yaml" / "complex_tests" / "test_1" / "python_files" / "main.py").absolute()
                    ),
                ),
                None,
            ),
        ],
    )
    def test_get_module_info(self, args, answer, exception):
        if exception:
            with pytest.raises(exception):
                get_module_info(*args)
        else:
            assert get_module_info(*args) == answer
