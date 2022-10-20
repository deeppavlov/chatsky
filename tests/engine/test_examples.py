from .examples._utils import run_auto_mode


def test_basics():
    from .examples.example_1_basics import actor, testing_dialog, logger

    run_auto_mode(actor, testing_dialog, logger)


def test_conditions():
    from .examples.example_2_conditions import actor, testing_dialog, logger

    run_auto_mode(actor, testing_dialog, logger)


def test_responses():
    from .examples.example_3_responses import actor, testing_dialog, logger

    run_auto_mode(actor, testing_dialog, logger)


def test_transitions():
    from .examples.example_4_transitions import actor, testing_dialog, logger

    run_auto_mode(actor, testing_dialog, logger)


def test_global_transitions():
    from .examples.example_5_global_transitions import actor, testing_dialog, logger

    run_auto_mode(actor, testing_dialog, logger)


def test_context_serialization():
    from .examples.example_6_context_serialization import run_auto_mode

    run_auto_mode()


def test_pre_response_processing():
    from .examples.example_7_pre_response_processing import actor, testing_dialog, logger

    run_auto_mode(actor, testing_dialog, logger)


def test_misc():
    from .examples.example_8_misc import actor, testing_dialog, logger

    run_auto_mode(actor, testing_dialog, logger)


def test_pre_transitions_processing():
    from .examples.example_9_pre_transitions_processing import actor, testing_dialog, logger

    run_auto_mode(actor, testing_dialog, logger)
