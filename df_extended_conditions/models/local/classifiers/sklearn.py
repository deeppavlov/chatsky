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

    IMPORT_ERROR_MESSAGE = None
except ImportError as e:
    BaseEstimator = object
    Pipeline = object

from ...sklearn import BaseSklearnModel


class SklearnClassifier(BaseSklearnModel):
    """
    SklearnClassifier utilizes Sklearn classification models to predict labels.

    Parameters
    -----------
    model: Optional[BaseEstimator]
        Sklearn-type model
    tokenizer: Optional[Union[BaseEstimator, Pipeline]] = None
        An Sklearn-type tokenizer, like TdidfVectorizer or CountVectorizer. Can also be a product
        of several preprocessors, unified with a pipeline.
    namespace_key: Optional[str]
        Name of the namespace in framework states that the model will be using.
    """

    def __init__(
        self,
        model: Optional[BaseEstimator] = None,
        tokenizer: Optional[Union[BaseEstimator, Pipeline]] = None,
        namespace_key: Optional[str] = None,
    ) -> None:
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
