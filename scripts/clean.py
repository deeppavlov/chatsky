from pathlib import Path
import shutil

# This functions cleans the outdated docs during local build
def clean_docs(output_dir: str = ""):
    shutil.rmtree("docs/build/" + output_dir, ignore_errors=True)
    shutil.rmtree("docs/tutorials", ignore_errors=True)
    shutil.rmtree("docs/source/apiref", ignore_errors=True)
    shutil.rmtree("docs/source/_misc", ignore_errors=True)
    shutil.rmtree("docs/source/tutorials", ignore_errors=True)
    shutil.rmtree("docs/source/_static/drawio", ignore_errors=True)
    shutil.rmtree("docs/source/drawio_src/**/export", ignore_errors=True)

# Ignored this function since it's unused.
def clean():
    clean_docs()
    shutil.rmtree(".pytest_cache", ignore_errors=True)
    shutil.rmtree("htmlcov", ignore_errors=True)
    shutil.rmtree("build", ignore_errors=True)
    Path(".coverage").unlink(missing_ok=True)
    for path in Path.cwd().glob("./*.egg-info"):
        shutil.rmtree(path, ignore_errors=True)
    for path in Path.cwd().glob("./**/__pycache__"):
        shutil.rmtree(path, ignore_errors=True)
