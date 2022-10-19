"""Parser tests."""
from pathlib import Path

import pytest

from dff.script.import_export.parser.utils.convenience_functions import get_module_name
from dff.script.import_export.parser.utils.exceptions import ModuleNotFoundParserError
from dff.script.import_export.parser.utils.module_metadata import get_module_info, ModuleType


current_dir = Path(__file__).parent


class TestSimpleFunctions:
    @pytest.mark.parametrize(
        "file,project_root_dir,answer",
        [
            (
                current_dir / "test_directory" / "__init__.py",
                current_dir / "test_directory",
                "test_directory.__init__"
            ),
            (
                current_dir / "test_directory" / "file.py",
                current_dir / "test_directory",
                "test_directory.file"
            ),
            (
                current_dir / "test_directory" / "another_package" / "__init__.py",
                current_dir / "test_directory",
                "test_directory.another_package.__init__",
            ),
            (
                current_dir / "test_directory" / "another_package" / "file.py",
                current_dir / "test_directory",
                "test_directory.another_package.file",
            ),
            (
                current_dir / "test_directory" / "dir" / "file.py",
                current_dir / "test_directory" / "dir",
                "file"
            ),
        ],
    )
    def test_get_module_name(self, file, project_root_dir, answer):
        assert get_module_name(file, project_root_dir) == answer

    @pytest.mark.parametrize(
        "args,answer,exception",
        [
            (
                ("file", current_dir / "test_directory"),
                (ModuleType.LOCAL, str((current_dir / "test_directory" / "file.py").absolute())),
                None,
            ),
            (
                ("file", current_dir / "test_directory" / "another_package"),
                (ModuleType.LOCAL, str((current_dir / "test_directory" / "another_package" / "file.py").absolute())),
                None,
            ),
            (
                ("another_package", current_dir / "test_directory"),
                (ModuleType.LOCAL, str((current_dir / "test_directory" / "another_package" / "__init__.py").absolute())),
                None,
            ),
            (
                ("..file", current_dir / "test_directory" / "another_package"),
                (ModuleType.LOCAL, str((current_dir / "test_directory" / "file.py").absolute())),
                None,
            ),
            (
                ("dir.file", current_dir / "test_directory"),
                (ModuleType.LOCAL, str((current_dir / "test_directory" / "dir" / "file.py").absolute())),
                None,
            ),
            (
                ("dir.file_does_not_exist", current_dir / "test_directory"),
                None,
                ModuleNotFoundParserError,
            ),
            (
                ("importlib.util", current_dir),
                (ModuleType.SYSTEM, "importlib"),
                None,
            ),
            (
                ("importlib.submodule_does_not_exist", current_dir),
                None,
                ModuleNotFoundParserError,
            ),
            (
                ("package_does_not_exist", current_dir),
                None,
                ModuleNotFoundParserError,
            ),
            (
                ("..nodes", current_dir / "test_py2yaml" / "complex_tests" / "test_1" / "python_files" / "flows"),
                (ModuleType.LOCAL, str((current_dir / "test_py2yaml" / "complex_tests" / "test_1" / "python_files" / "nodes" / "__init__.py").absolute())),
                None,
            ),
            (
                ("..nodes.fallback_node", current_dir / "test_py2yaml" / "complex_tests" / "test_1" / "python_files" / "flows"),
                (ModuleType.LOCAL, str((current_dir / "test_py2yaml" / "complex_tests" / "test_1" / "python_files" / "nodes" / "fallback_node.py").absolute())),
                None,
            ),
            (
                ("..main", current_dir / "test_py2yaml" / "complex_tests" / "test_1" / "python_files" / "flows"),
                (ModuleType.LOCAL, str((current_dir / "test_py2yaml" / "complex_tests" / "test_1" / "python_files" / "main.py").absolute())),
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
