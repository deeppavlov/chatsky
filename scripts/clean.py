import glob
import pathlib
import shutil


def clean_docs():
    shutil.rmtree("docs/build", ignore_errors=True)
    shutil.rmtree("docs/tutorials", ignore_errors=True)
    shutil.rmtree("docs/source/apiref", ignore_errors=True)
    shutil.rmtree("docs/source/tutorials", ignore_errors=True)


def clean():
    clean_docs()
    shutil.rmtree(".pytest_cache", ignore_errors=True)
    shutil.rmtree("htmlcov", ignore_errors=True)
    shutil.rmtree("build", ignore_errors=True)
    pathlib.Path(".coverage").unlink(missing_ok=True)
    pathlib.Path("poetry.lock").unlink(missing_ok=True)
    for path in glob.glob("*.egg-info"):
        shutil.rmtree(path, ignore_errors=True)
    for path in glob.glob("**/__pycache__", recursive=True):
        shutil.rmtree(path, ignore_errors=True)
