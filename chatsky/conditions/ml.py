"""
ML Conditions
------------

This module provides condition functions for ML annotations.
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
        # and store them in framework_data with the pipeline_model as a key
        labels = dict()
        if ctx.framework_data.models_labels.get(self.pipeline_model, {}) != {}:
            # If the labels are already present, use them
            labels = ctx.framework_data.models_labels[self.pipeline_model]
        else:
            if ctx.last_request and ctx.last_request.text:
                labels = await model.predict(ctx.last_request.text)
        # Store the labels in the framework_data
        ctx.framework_data.models_labels[self.pipeline_model] = labels

        label_score = labels.get(self.label, 0)
        return label_score >= self.threshold
