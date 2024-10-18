from __future__ import annotations
import os
import shutil
from pathlib import Path, PurePath
from subprocess import CalledProcessError
from typing import TYPE_CHECKING, Any, Iterable

from sphinx_polyversion.builder import Builder, BuildError
from sphinx_polyversion.environment import Environment
from sphinx_polyversion.json import GLOBAL_ENCODER, JSONable

if TYPE_CHECKING:
    import json

import scripts.doc
from scripts.clean import clean_docs
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

        # TODO: Need to sort tags, to add the right link for the "latest" tag
        #  (Let output_dir == "v0.9.0", but github-actions-deploy dir == "latest", unless it isn't, of course,
        #  depends on what we decide).
        #  Then the links will be all wrong if they're not changed here.
        # Making GitHub links version dependent in tutorials and API reference
        accepted_branch_prefixes = ["feat", "fix", "test", "docs", "style", "refactor", "chore"]
        output_dir_list = str(output_dir).split('/')
        if output_dir_list[-2] in accepted_branch_prefixes:
            doc_version = output_dir_list[-2] + "/" + output_dir_list[-1]
        else:
            doc_version = output_dir_list[-1]

        example_links_file = Path(source_dir) / "_templates" / "example-links.html"
        source_links_file = Path(source_dir) / "_templates" / "source-links.html"
        for links_file in [example_links_file, source_links_file]:
            with open(links_file, "r") as file:
                contents = file.read()
                contents = contents.replace('DOC_VERSION', doc_version)
                # links_file.write_text(contents)

            with open(links_file, "w") as file:
                file.write(contents)

        # Cleaning outdated documentation build
        clean_docs(str(output_dir))

        # Running Chatsky custom funcs before doc building
        root_dir = environment.path.absolute()
        scripts.doc.pre_sphinx_build_funcs(str(root_dir))
        # setup_module.setup(str(root_dir))

        # Using the newest conf.py file instead of the old one
        new_sphinx_configs = True
        if new_sphinx_configs:
            newer_conf_path = (os.getcwd() + "/docs/source/conf.py")
            older_conf_path = str(source_dir) + "/conf.py"
            # Saving the old conf.py file for future use.
            shutil.copyfile(older_conf_path, str(source_dir) + "/old_conf.py")
            shutil.copyfile(newer_conf_path, older_conf_path)

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
