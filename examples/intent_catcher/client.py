import os
import requests


def test_respond():
    url = f"http://{os.getenv('SERVICE_HOST')}:{os.getenv('SERVICE_PORT')}/respond"

    contexts = ["I want to order food", "cancel_the_order"]
    result = requests.post(url, json={"dialog_contexts": contexts}).json()
    assert [len(sample[0]) > 0 and sample[1] > 0.0 for sample in result], f"Got\n{result}\n, something is wrong"
    print("Success")


if __name__ == "__main__":
    test_respond()
