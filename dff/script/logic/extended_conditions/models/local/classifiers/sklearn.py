"""
Sklearn Classifier
*******************

This module provides an adapter interface for Sklearn models.
Use Sklearn classifiers to achieve great results on a limited set of data.
"""
from typing import Optional, Union

try:
    from sklearn.base import BaseEstimator
    from sklearn.pipeline import Pipeline

    sklearn_available = True
except ImportError as e:
    BaseEstimator = object
    Pipeline = object
    sklearn_available = False

from ...sklearn import BaseSklearnModel


class SklearnClassifier(BaseSklearnModel):
    """
    SklearnClassifier utilizes Sklearn classification models to predict labels.

    :param model: Sklearn-type model
    :param tokenizer: An Sklearn-type tokenizer, like TdidfVectorizer or CountVectorizer. Can also be a product
        of several preprocessors, unified with a pipeline.
    :param namespace_key: Name of the namespace in framework states that the model will be using.
    """

    def __init__(
        self,
        model: Optional[BaseEstimator] = None,
        tokenizer: Optional[Union[BaseEstimator, Pipeline]] = None,
        namespace_key: Optional[str] = None,
    ) -> None:
        if not sklearn_available:
            raise ImportError("`sklearn` package missing. Try `pip install dff[sklearn]`.")
        assert model is not None, "model parameter is required."
        super().__init__(model, tokenizer, namespace_key)

    def predict(self, request: str) -> dict:
        if hasattr(self._pipeline, "predict_proba"):
            probas = self._pipeline.predict_proba([request])[0]
            labels = self._pipeline._final_estimator.classes_
            result = {key: value for key, value in zip(labels, probas)}
        else:
            label = self._pipeline.predict([request])[0]
            result = {label: 1}
        return result
