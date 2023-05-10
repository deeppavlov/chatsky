from pathlib import Path
from filecmp import dircmp
from typing import List


def assert_files_equal(file1: Path, file2: Path):
    with open(file1, "r") as first, open(file2, "r") as second:
        assert list(first.readlines()) == list(second.readlines())


def assert_dirs_equal(dir1: Path, dir2: Path):
    subdir_stack: List[str] = []

    def _assert_dir_eq(dir_cmp: dircmp):
        assert len(dir_cmp.left_only) == 0
        assert len(dir_cmp.right_only) == 0
        for diff_file in dir_cmp.diff_files:
            with open(dir1.joinpath(*subdir_stack, diff_file), "r") as first, open(
                dir2.joinpath(*subdir_stack, diff_file), "r"
            ) as second:
                assert list(first.readlines()) == list(second.readlines())
        for name, subdir in dir_cmp.subdirs.items():
            subdir_stack.append(name)
            _assert_dir_eq(subdir)
            subdir_stack.pop()

    _assert_dir_eq(dircmp(dir1, dir2))
