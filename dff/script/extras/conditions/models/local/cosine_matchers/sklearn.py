"""
Sklearn Cosine Matcher
----------------------

This module provides an adapter interface for sklearn models.
It uses Sklearn BOW representations and other features to compute distances between utterances.
"""
from typing import Optional

from dff.script.extras.conditions.models.sklearn import BaseSklearnModel, sklearn_available
from dff.script.extras.conditions.dataset import Dataset
from dff.script.extras.conditions.models.local.cosine_matchers.cosine_matcher_mixin import CosineMatcherMixin


class SklearnMatcher(CosineMatcherMixin, BaseSklearnModel):
    """
    SklearnMatcher utilizes embeddings from Sklearn models to measure
    proximity between utterances and pre-defined labels.

    :param model: Sklearn-type model
    :param dataset: Labels for the matcher. The prediction output depends on proximity to different labels.
    :param tokenizer: An Sklearn-type tokenizer, like TdidfVectorizer or CountVectorizer. Can also be a product
        of several preprocessors, unified with a pipeline.
    :param namespace_key: Name of the namespace in framework states that the model will be using.
    """

    def __init__(
        self,
        model: object = None,
        dataset: Optional[Dataset] = None,
        tokenizer: object = None,
        namespace_key: Optional[str] = None,
    ) -> None:
        if not sklearn_available:
            raise ImportError("`sklearn` package missing. Try `pip install dff[sklearn]`.")
        CosineMatcherMixin.__init__(self, dataset=dataset)
        BaseSklearnModel.__init__(self, model=model, tokenizer=tokenizer, namespace_key=namespace_key)
