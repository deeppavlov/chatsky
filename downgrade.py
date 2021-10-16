# %%

import re
import pathlib

native_type_patterns = {re.compile(r"\b(" + t + r")\["): t.capitalize() + "[" for t in ["dict", "list", "tuple"]}
cache_patterns = {re.compile(r"\bfunctools.cache\b"): "functools.lru_cache"}
fstring_patterns = {re.compile(r"\=\}"): "}"}
# %%

rep_root = pathlib.Path(".")
py_files = sum([list(rep_root.glob(glob)) for glob in ["tests/*.py", "examples/*.py", "dff/*.py", "dff/core/*.py"]], [])
# %%

for py_file in py_files:
    text = py_file.read_text()
    if any([i.search(text) for i in native_type_patterns.keys()]):
        text = "from typing import Dict, List, Tuple\n{}".format(text)
        for pat, replace in native_type_patterns.items():
            text = pat.sub(replace, text)
    for pat, replace in cache_patterns.items():
        text = pat.sub(replace, text)
    py_file.write_text(text)
