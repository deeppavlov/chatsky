"""
Custom Classifier
==================

In this module, we show how you can implement a classifier.
"""
import pickle

from dff.script.logic.extended_conditions.models.base_model import BaseModel

"""
In order to create your own classifier, create a child class of the `BaseModel` abstract type. 

`BaseModel` only has one abstract method, `predict`, that should necessarily be overridden. 
The signature of the method is the following: it takes a request string and returns a dictionary of class labels 
and their respective probabilities. 

You can override the rest of the methods, namely `save`, `load`, `fit` and `transform` at your own convenience, 
e.g. lack of those will not raise an error. 

* `fit` should take a new dataset and retrain / update the underlying model.
* `transform` should take a request string and produce a vector.
* `save` and `load` are self-explanatory.
"""


class MyCustomClassifier(BaseModel):
    def __init__(self, swear_words: list, namespace_key: str = "default") -> None:
        self.swear_words = swear_words or ["hell", "damn", "curses"]
        super().__init__(namespace_key)

    def predict(self, request: str) -> dict:
        probs = {}

        if any([word in request for word in self.swear_words]):
            probs["swearing"] = 1.0

        return probs

    def save(self, filename: str):
        with open(filename, "wb+") as file:
            pickle.dump(self.swear_words, file)

    @classmethod
    def load(cls, filename: str, namespace_key: str):
        with open(filename, "rb") as file:
            swear_words = pickle.load(file)
        return cls(swear_words=swear_words, namespace_key=namespace_key)
