"""
Conditions
------------

This module provides condition functions for annotation processing.
"""

from chatsky import Context
from chatsky.conditions.standard import BaseCondition


class HasLabel(BaseCondition):
    """
    Use this condition, when you need to check, whether the probability
    of a particular label for the last annotated user utterance surpasses the threshold.
    """

    label: str
    """
    The name of the label to check.
    """
    pipeline_model: str
    """
    The name of the model in Pipeline to use for label checking.
    """
    threshold: float = 0.9
    """
    The minimal label probability that triggers a positive response.
    """
    # TODO: consider adding history param

    async def call(self, ctx: Context) -> bool:
        model = ctx.pipeline.models[self.pipeline_model]
        # Predict labels for the last request
        # and store them in framework_data with uuid of the model as a key
        if model.model_id not in ctx.framework_data.models_labels:
            await model(ctx)
        if model.model_id is not None:
            return ctx.framework_data.models_labels.get(model.model_id, {}).get(self.label, 0) >= self.threshold
        scores = [item.get(self.label, 0) for item in ctx.framework_data.models_labels.values()]
        comparison_array = [item >= self.threshold for item in scores]
        return any(comparison_array)
