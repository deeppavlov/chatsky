from __future__ import annotations
import enum
import os
import sys
import shutil
import importlib.util
from logging import getLogger
from pathlib import Path, PurePath
from subprocess import CalledProcessError
from typing import TYPE_CHECKING, Any, Iterable

from sphinx_polyversion.builder import Builder, BuildError
from sphinx_polyversion.environment import Environment
from sphinx_polyversion.json import GLOBAL_ENCODER, JSONable

if TYPE_CHECKING:
    import json

import scripts.doc
from sphinx_polyversion.sphinx import CommandBuilder, Placeholder


class DffSphinxBuilder(CommandBuilder):
    def __init__(
        self,
        source: str | PurePath,
        args: Iterable[str] = [],
        encoder: json.JSONEncoder | None = None,
        pre_cmd: Iterable[str | Placeholder] | None = None,
        post_cmd: Iterable[str | Placeholder] | None = None,
    ) -> None:
        cmd: Iterable[str | Placeholder] = [
            "sphinx-build",
            "--color",
            *args,
            Placeholder.SOURCE_DIR,
            Placeholder.OUTPUT_DIR,
        ]
        super().__init__(
            source,
            cmd,
            encoder=encoder,
            pre_cmd=pre_cmd,
            post_cmd=post_cmd,
        )
        self.args = args
        
    async def build(
        self, environment: Environment, output_dir: Path, data: JSONable
    ) -> None:
        """
        Build and render a documentation.

        This method runs the command the instance was created with.
        The metadata will be passed to the subprocess encoded as json
        using the `POLYVERSION_DATA` environment variable.

        Parameters
        ----------
        environment : Environment
            The environment to use for building.
        output_dir : Path
            The output directory to build to.
        data : JSONable
            The metadata to use for building.
        """
        self.logger.info("Building...")
        source_dir = str(environment.path.absolute() / self.source)

        def replace(v: Any) -> str:
            if v == Placeholder.OUTPUT_DIR:
                return str(output_dir)
            if v == Placeholder.SOURCE_DIR:
                return source_dir
            return str(v)

        env = os.environ.copy()
        env["POLYVERSION_DATA"] = self.encoder.encode(data)

        cmd = tuple(map(replace, self.cmd))

        # create output directory
        output_dir.mkdir(exist_ok=True, parents=True)

        # Importing version-dependent module setup.py
        root_dir = environment.path.absolute()
        os.system("ls" + str(source_dir))
        spec = importlib.util.spec_from_file_location("setup", str(source_dir) + "/setup.py")
        setup_module = importlib.util.module_from_spec(spec)
        sys.modules["setup"] = setup_module
        spec.loader.exec_module(setup_module)
        
        """
        # Cleaning outdated documentation build
        sphinx.make_main(["-M", "clean", str(source_dir), str(output_dir)])
        """
        
        # doing DFF funcs before doc building
        scripts.doc.dff_funcs(str(root_dir))
        setup_module.setup(str(root_dir), str(output_dir))
        
        # Replacing old conf.py file with the newest one
        # This shouldn't be there in builders for older versions.
        newer_conf_path = (os.getcwd() + "/docs/source/conf.py")
        older_conf_path = str(source_dir) + "/conf.py"
        shutil.copyfile(newer_conf_path, older_conf_path)
        
        # Removing Jekyll theming
        open(str(output_dir) + '/.nojekyll', 'a')
        
        # pre hook
        if self.pre_cmd:
            out, err, rc = await environment.run(*map(replace, self.pre_cmd), env=env)
            if rc:
                raise BuildError from CalledProcessError(rc, " ".join(cmd), out, err)

        # build command
        out, err, rc = await environment.run(*cmd, env=env)

        self.logger.debug("Installation output:\n %s", out)
        if rc:
            raise BuildError from CalledProcessError(rc, " ".join(cmd), out, err)

        # post hook
        if self.post_cmd:
            out, err, rc = await environment.run(*map(replace, self.post_cmd), env=env)
            if rc:
                raise BuildError from CalledProcessError(rc, " ".join(cmd), out, err)

