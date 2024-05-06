class VKDummy:
    """Class for logging VK_Interface requests.
    """
    def __init__(self):
        self.responses = []
        self.requests = []
    
    def __getattribute__(self, name):
        def method(*args, **kwargs):
            self.responses.append((name, args, kwargs))
        if hasattr(self, name):
            return super(self).__getattribute__(name)
        return method


    def dummy_post(self, request_method: str, data: dict):
        """Function for logging POST requests that will override original `requests.post` method.
        Willl return dummy objects for requests that require response.

        Args:
            request (_str_): method to request
            data (_dict_): data to post
        """
        self.requests.append((request_method, data))
        if "getMessagesUploadServer" in request_method:
            return {"response": {"upload_url": "https://dummy_url"}}
        elif "save" in request_method:
            return {"response": [{"owner": "dummy", "id": "123"}]}
        elif "getLongPollServer" in request_method:
            return {"response": {"server": "dummy_url", "key": "dummy_key", "ts": "dummy_ts"}}
