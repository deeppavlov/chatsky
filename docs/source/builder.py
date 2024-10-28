from __future__ import annotations
import os
import sys
import shutil
import importlib.util
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


class ChatskySphinxBuilder(CommandBuilder):
    def __init__(
        self,
        source: str | PurePath,
        args: Iterable[str] = [],
        encoder: json.JSONEncoder | None = None,
        pre_cmd: Iterable[str | Placeholder] | None = None,
        post_cmd: Iterable[str | Placeholder] | None = None,
    ) -> None:
        cmd: Iterable[str | Placeholder] = [
            "poe",
            "tmp_docs",
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
        source_dir = str(environment.path.absolute() / self.source)

        # create output directory
        output_dir.mkdir(exist_ok=True, parents=True)

        # Importing version-dependent module setup.py
        root_dir = environment.path.absolute()
        spec = importlib.util.spec_from_file_location("setup", str(source_dir) + "/setup.py")
        setup_module = importlib.util.module_from_spec(spec)
        sys.modules["setup"] = setup_module
        spec.loader.exec_module(setup_module)

        doc_version_path = str(output_dir).split('/')[-1] + '/'
        setup_configs = {
            "doc_version": doc_version_path,
            "root_dir": str(root_dir),
            "apiref_destination": Path("apiref"),
            "tutorials_source": str(root_dir) + "/tutorials",
            "tutorials_destination": str(root_dir) + "/docs/source/tutorials",
        }
        print(setup_configs)

        # Running Chatsky custom funcs before doc building
        module_dir = environment.path.absolute() / "chatsky"
        print("source_dir:", source_dir)
        print("module_dir:", module_dir)
        scripts.doc.pre_sphinx_build_funcs(str(source_dir), str(module_dir))
        setup_module.setup(setup_configs)

        # Using the newest conf.py file instead of the old one
        new_sphinx_configs = True
        if new_sphinx_configs:
            newer_conf_path = (os.getcwd() + "/docs/source/conf.py")
            older_conf_path = str(source_dir) + "/conf.py"
            shutil.copyfile(newer_conf_path, older_conf_path)

        """
        # TODO: Move the code before to a .py file and throw it's execution into pre_cmd right here.
        # TODO: Try printing out the env to see what env variables are there.
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
        """
        return super().build(
            environment,
            output_dir,
            data
        )
