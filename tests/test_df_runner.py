from df_runner import Runner

from examples import cli_runner


def test_cli():
    assert isinstance(cli_runner.runner, Runner)
