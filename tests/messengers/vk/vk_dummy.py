class VKDummy:
    def __init__(self):
        self.responses = []
    
    def __getattribute__(self, name):
        def method(*args, **kwargs):
            self.responses.append((name, args, kwargs))
        if name in ("responses",):
            return super(self).__getattribute__(name)
        return method
