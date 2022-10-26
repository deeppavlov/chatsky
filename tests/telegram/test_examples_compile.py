"This script ensures that example scripts can successfully compile and are ready to run"

def test_basics():
    from .examples.no_runner.basic_bot import bot, actor

    assert bot
    assert actor
    from .examples.no_runner.pictures import bot, actor

    assert bot
    assert actor
    from .examples.no_runner.commands_and_buttons import bot, actor

    assert bot
    assert actor


def test_generics():
    from .examples.generic_response.callback_queries import bot, provider, runner

    assert bot
    assert provider
    assert runner
    from .examples.generic_response.pictures import bot, provider, runner

    assert bot
    assert provider
    assert runner


def test_runner():
    from .examples.basics.flask import bot, provider, runner

    assert bot
    assert provider
    assert runner
    from .examples.basics.polling import bot, provider, runner

    assert bot
    assert provider
    assert runner
