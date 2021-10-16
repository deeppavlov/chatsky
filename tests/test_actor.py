# %%

from dff.core import Actor


def positive_test(samples, custom_class):
    results = []
    for sample in samples:
        try:
            res = custom_class(**sample)
            results += [res]
        except Exception as exeption:
            raise Exception(f"{sample} gets {exeption}")
    return results


def negative_test(samples, custom_class):
    for sample in samples:
        try:
            custom_class(**sample)
        except Exception:  # TODO: spetial tyupe of exceptions
            continue
        raise Exception(f"{sample} can not be passed")


def test_actor():
    try:
        Actor({"flow": {"node1": {}}}, start_label=("flow1", "node1"))
    except ValueError:
        pass
    try:
        Actor({"flow": {"node1": {}}}, start_label=("flow", "node1"), fallback_label=("flow1", "node1"))
    except ValueError:
        pass
