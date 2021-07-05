import random


class StochasticOptions(dict):
    def __init__(self, options):
        if isinstance(options, dict):
            dict.__init__(self, options)
        else:
            dict.__init__(self, {k: 1.0 for k in options})

    def select(self):
        options = list(self.keys())
        assert len(options) > 0
        total = sum(self.values())
        if total <= 0.0:
            return random.choice(options)
        thresholds = []
        curr = 0
        for t in options:
            prob = self[t] / total
            curr += prob
            thresholds.append(curr)
        r = random.uniform(0, 1.0)
        for i, threshold in enumerate(thresholds):
            if r < threshold:
                return options[i]
        return options[-1]
