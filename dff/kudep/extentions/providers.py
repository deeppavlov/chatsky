responses = {"weather": lambda vars: "it's raining"}


def fact_provider(topic):
    return responses[topic]
