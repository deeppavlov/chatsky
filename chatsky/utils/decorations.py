class classproperty:
    def __init__(self, f):
        self.f = f

    def __get__(self, _, owner):
        return self.f(owner)
