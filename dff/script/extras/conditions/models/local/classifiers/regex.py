"""
Regex Classifier
----------------

This module provides a regex-based annotator model.
Initialize it with a :py:class:`~Dataset` with regex-compliant examples.
"""
import re
from typing import Optional, Union

from dff.script.extras.conditions.models.base_model import ExtrasBaseModel
from dff.script.extras.conditions.dataset import Dataset


class RegexModel:
    """
    RegexModel implements utterance classification based on regex rules.

    :param dataset: Labels for the matcher. The prediction output depends on proximity to different labels.
    """

    def __init__(self, dataset: Dataset):
        self.dataset = dataset

    def __call__(self, request: str, **re_kwargs):
        result = {}
        for label, dataset_item in self.dataset.items.items():
            matches = [
                re.search(item, request, **re_kwargs) for item in dataset_item.samples
            ]  # TODO: replace compilation to the init
            if any(map(bool, matches)):
                result[label] = 1.0

        return result


class RegexClassifier(ExtrasBaseModel):
    """
    RegexClassifier wraps a :py:class:`~RegexModel` for label annotation.

    Parameters
    -----------
    model: RegexModel
        An instance of df_extended_conditions' RegexModel.
    namespace_key: Optional[str]
        Name of the namespace in framework states that the model will be using.
    re_kwargs: Optional[dict]
        re arguments override.
    """

    def __init__(
        self,
        model: Union[RegexModel, Dataset],
        namespace_key: str,
        re_kwargs: Optional[dict] = None,
    ) -> None:
        super().__init__(namespace_key=namespace_key)
        self.re_kwargs = re_kwargs or {"flags": re.IGNORECASE}
        # instantiate if DatasetItem Collection has been passed
        self.model = model if isinstance(model, RegexModel) else RegexModel(model)

    def fit(self, dataset: Dataset):
        self.model.dataset = dataset

    def predict(self, request: str) -> dict:
        return self.model(request, **self.re_kwargs)
