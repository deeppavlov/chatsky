class VKDummy:
    def __init__(self):
        self.requests = []
    
    def __getattribute__(self, name):
        def send_message(*args, **kwargs):
            self.requests.append((name, args, kwargs))
        return send_message
    
