import subprocess
from sphinx_polyversion.pyvenv import Poetry


class ChatskyPoetry(Poetry):
    async def __aenter__(self):
        # Adding sphinx-polyversion to local dependencies
        poetry_args = ["poetry", "add", "sphinx-polyversion", "--group", "docs"]
        poetry_subprocess = subprocess.Popen(poetry_args, cwd=self.path)
        poetry_subprocess.wait()
        await super().__aenter__()
