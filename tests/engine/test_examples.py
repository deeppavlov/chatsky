def test_basics():
    from .examples.example_1_basics import run_test

    run_test()


def test_conditions():
    from .examples.example_2_conditions import run_test

    run_test()


def test_responses():
    from .examples.example_3_responses import run_test

    run_test()


def test_transitions():
    from .examples.example_4_transitions import run_test

    run_test()


def test_global_transitions():
    from .examples.example_5_global_transitions import run_test

    run_test()


def test_context_serialization():
    from .examples.example_6_context_serialization import run_test

    run_test()


def test_pre_response_processing():
    from .examples.example_7_pre_response_processing import run_test

    run_test()


def test_misc():
    from .examples.example_8_misc import run_test

    run_test()


def test_pre_transitions_processing():
    from .examples.example_9_pre_transitions_processing import run_test

    run_test()
