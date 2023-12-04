"""
Conditions
------------

This module provides condition functions for annotation processing.
"""
from typing import Callable, Optional, List
from functools import singledispatch

try:
    from sklearn.metrics.pairwise import cosine_similarity

    sklearn_available = True
except ImportError:
    sklearn_available = False
from dff.script import Context
from dff.pipeline import Pipeline
from dff.script.extras.conditions.dataset import DatasetItem
from dff.script.extras.conditions.utils import LABEL_KEY
from dff.script.extras.conditions.models.base_model import ExtrasBaseModel


@singledispatch
def has_cls_label(label, namespace: Optional[str] = None, threshold: float = 0.9):
    """
    Use this condition, when you need to check, whether the probability
    of a particular label for the last annotated user utterance surpasses the threshold.

    :param label: String name or a reference to a DatasetItem object, or a collection thereof.
    :param namespace: Namespace key of a particular model that should detect the dataset_item.
        If not set, all namespaces will be searched for the required dataset_item.
    :param threshold: The minimal label probability that triggers a positive response
        from the function.
    """
    raise NotImplementedError


@has_cls_label.register(str)
def _(label, namespace: Optional[str] = None, threshold: float = 0.9):
    def has_cls_label_innner(ctx: Context, _) -> bool:
        if LABEL_KEY not in ctx.framework_states:
            return False
        if namespace is not None:
            return ctx.framework_states[LABEL_KEY].get(namespace, {}).get(label, 0) >= threshold
        scores = [item.get(label, 0) for item in ctx.framework_states[LABEL_KEY].values()]
        comparison_array = [item >= threshold for item in scores]
        return any(comparison_array)

    return has_cls_label_innner


@has_cls_label.register(DatasetItem)
def _(label, namespace: Optional[str] = None, threshold: float = 0.9) -> Callable[[Context, Pipeline], bool]:
    def has_cls_label_innner(ctx: Context, _) -> bool:
        if LABEL_KEY not in ctx.framework_states:
            return False
        if namespace is not None:
            return ctx.framework_states[LABEL_KEY].get(namespace, {}).get(label.label, 0) >= threshold
        scores = [item.get(label.label, 0) for item in ctx.framework_states[LABEL_KEY].values()]
        comparison_array = [item >= threshold for item in scores]
        return any(comparison_array)

    return has_cls_label_innner


@has_cls_label.register(list)
def _(label, namespace: Optional[str] = None, threshold: float = 0.9):
    def has_cls_label_innner(ctx: Context, pipeline: Pipeline) -> bool:
        if LABEL_KEY not in ctx.framework_states:
            return False
        scores = [has_cls_label(item, namespace, threshold)(ctx, pipeline) for item in label]
        for score in scores:
            if score >= threshold:
                return True
        return False

    return has_cls_label_innner


def has_match(
    model: ExtrasBaseModel,
    positive_examples: Optional[List[str]],
    negative_examples: Optional[List[str]] = None,
    threshold: float = 0.9,
):
    """
    Use this condition, if you need to check whether the last request matches
    any of the pre-defined intent utterances.
    The model passed to this function should be in the fit state.

    :param model: Any model from the :py:mod:`~dff.script.extras.conditions.models.local.cosine_matchers` module.
    :param positive_examples: Utterances that the request should match.
    :param negative_examples: Utterances that the request should not match.
    :param threshold: Similarity threshold that triggers a positive response from the function.
    """
    if negative_examples is None:
        negative_examples = []

    def has_match_inner(ctx: Context, _) -> bool:
        if not (ctx.last_request and ctx.last_request.text):
            return False
        input_vector = model.transform(ctx.last_request.text)
        positive_vectors = [model.transform(item) for item in positive_examples]
        negative_vectors = [model.transform(item) for item in negative_examples]
        positive_sims = [cosine_similarity(input_vector, item)[0][0] for item in positive_vectors]
        negative_sims = [cosine_similarity(input_vector, item)[0][0] for item in negative_vectors]
        max_pos_sim = max(positive_sims)
        max_neg_sim = 0 if len(negative_sims) == 0 else max(negative_sims)
        return bool(max_pos_sim > threshold > max_neg_sim)

    return has_match_inner
