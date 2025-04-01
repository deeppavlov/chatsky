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

    :param label: String name or a reference to a DatasetItem object, or a collection thereof.
    :param namespace: Namespace key of a particular model that should detect the dataset_item.
        If not set, all namespaces will be searched for the required dataset_item.
    :param threshold: The minimal label probability that triggers a positive response
        from the function.
    """

    label: str
    pipeline_model: str
    threshold: float = 0.9
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
