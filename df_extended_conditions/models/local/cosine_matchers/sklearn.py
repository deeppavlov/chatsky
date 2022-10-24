"""
Sklearn Cosine Matcher
--------------------------

This module provides an adapter interface for sklearn models.
It uses Sklearn BOW representations and other features to compute distances between utterances.
"""
from typing import Optional, Union

try:
    from sklearn.base import BaseEstimator
    from sklearn.pipeline import Pipeline

    IMPORT_ERROR_MESSAGE = None
except ImportError as e:
    BaseEstimator = object
    IMPORT_ERROR_MESSAGE = e.msg

from ...sklearn import BaseSklearnModel
from ....dataset import Dataset
from .cosine_matcher_mixin import CosineMatcherMixin


class SklearnMatcher(CosineMatcherMixin, BaseSklearnModel):
    """
    SklearnMatcher utilizes embeddings from Sklearn models to measure
    proximity between utterances and pre-defined labels.

    Parameters
    -----------
    model: Optional[BaseEstimator]
        Sklearn-type model
    dataset: Dataset
        Labels for the matcher. The prediction output depends on proximity to different labels.
    tokenizer: Optional[Union[BaseEstimator, Pipeline]] = None
        An Sklearn-type tokenizer, like TdidfVectorizer or CountVectorizer. Can also be a product
        of several preprocessors, unified with a pipeline.
    namespace_key: Optional[str]
        Name of the namespace in framework states that the model will be using.
    """

    def __init__(
        self,
        model: Optional[BaseEstimator] = None,
        dataset: Optional[Dataset] = None,
        tokenizer: Optional[Union[BaseEstimator, Pipeline]] = None,
        namespace_key: Optional[str] = None,
    ) -> None:
        CosineMatcherMixin.__init__(self, dataset=dataset)
        BaseSklearnModel.__init__(self, model=model, tokenizer=tokenizer, namespace_key=namespace_key)
