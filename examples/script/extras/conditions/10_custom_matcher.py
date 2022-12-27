# %% [markdown]
"""
# 10. Custom Matcher

This module demonstrates the way in which a custom matcher can be implemented.
"""


# %%
from dff.script.extras.conditions.models.base_model import BaseModel
from dff.script.extras.conditions.models.local.cosine_matchers.cosine_matcher_mixin import (
    CosineMatcherMixin,
)


# %% [markdown]
"""
To build  your own cosine matcher, you should inherit
from the `CosineMatcherMixin` and from the `BaseModel`,
with the former taking precedence.
This requires the `__init__` method to take `dataset` argument.

In your class, override the `transform` method
that is used to obtain a two-dimensional vector (optimally, a Numpy array) from a string.

Unlike the classifier case, the `predict` method is already implemented for you,
so you don't have to tamper with it.

Those two steps should suffice to get your matcher up and running.
You can override the rest of the methods, namely `save`, `load`, and `fit` at your own convenience,
e.g. lack of those will not raise an error.

* `fit` should take a new dataset and retrain / update the underlying model.
* `save` and `load` are self-explanatory.
    You may use pickle, utils from joblib, or any other serializer.

"""


# %%
class MyCustomMatcher(CosineMatcherMixin, BaseModel):
    def __init__(self, model, dataset, namespace_key) -> None:
        CosineMatcherMixin.__init__(self, dataset)
        BaseModel.__init__(self, namespace_key)
        self.model = model

    def transform(self, request: str):
        vector = self.model(request)
        return vector
