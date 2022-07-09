import typing as tp
from pathlib import Path
import json
import logging
import importlib.util

try:
    import importlib.metadata
    import sys

    def get_metadata(module: str) -> tp.Optional[str]:
        """Get module metadata.

        Return distribution information:

        * For distributions installed via VCS: "{vcs}+{url}@{commit}"
        * For distributions installed via pypi: "{project_name}=={version}"
        * None otherwise

        :param module: str, module name
        :return: Optional[str], module metadata
        """
        # find vcs info
        try:
            for source in [
                directory.read_text("direct_url.json")
                for directory in importlib.metadata.MetadataPathFinder.find_distributions(
                    context=importlib.metadata.DistributionFinder.Context(name=module, path=sys.path)
                )
            ]:
                if source is not None:
                    vcs_info = json.loads(source)
                    return f"{vcs_info['vcs_info']['vcs']}+{vcs_info['url']}@{vcs_info['vcs_info']['commit_id']}"
        except (
            importlib.metadata.PackageNotFoundError,
            KeyError,
            json.decoder.JSONDecodeError,
        ) as e:
            logging.debug(e)
        try:
            # find modules installed via pip
            dist = importlib.metadata.distribution(module)
            return f"{dist.metadata['Name']}=={dist.version}"
        except (importlib.metadata.PackageNotFoundError, AttributeError, KeyError) as e:
            logging.debug(e)
            return None

    def get_location(module: str, working_dir: tp.Union[str, Path]) -> tp.Optional[str]:
        """Get module location.

        Find a module location.

        If module is located inside working_dir return its relative path. Return absolute path otherwise
        """
        spec = importlib.util.find_spec(module)
        if spec and spec.origin:
            try:
                return str(Path(spec.origin).relative_to(Path(working_dir).absolute()))
            except ValueError as e:
                logging.warning(f"File {spec.origin} not in {working_dir}.")
                logging.debug(e)
                return str(Path(spec.origin).absolute())


except ImportError:
    import pkg_resources

    def get_metadata(module: str) -> tp.Optional[str]:
        """Get module metadata.

        Return distribution information:

        * For distributions installed via VCS: "{vcs}+{url}@{commit}"
        * For distributions installed via pypi: "{project_name}=={version}"
        * None otherwise

        :param module: str, module name
        :return: Optional[str], module metadata
        """
        # find distribution
        try:
            dist = pkg_resources.get_distribution(module)
        except pkg_resources.DistributionNotFound as e:
            logging.debug(e)
            return None

        # find VCS info
        try:
            vcs_info = json.load((Path(dist.egg_info) / "direct_url.json").open("r"))  # type: ignore
            return f"{vcs_info['vcs_info']['vcs']}+{vcs_info['url']}@{vcs_info['vcs_info']['commit_id']}"
        except (
            AttributeError,
            FileNotFoundError,
            json.decoder.JSONDecodeError,
            KeyError,
        ) as e:
            logging.debug(e)

        # find distribution pypi info
        try:
            return f"{dist.project_name}=={dist.version}"
        except AttributeError as e:
            logging.debug(e)


    def get_location(module: str, working_dir: tp.Union[str, Path]) -> tp.Optional[str]:
        """Get module location.

        Find a module location.

        If module is located inside working_dir return its relative path. Return absolute path otherwise
        """
        spec = importlib.util.find_spec(module)
        if spec and spec.origin:
            try:
                return str(Path(spec.origin).relative_to(Path(working_dir)))
            except ValueError as e:
                logging.warning(f"File {spec.origin} not in {working_dir}.")
                logging.debug(e)
                return str(Path(spec.origin).absolute())

