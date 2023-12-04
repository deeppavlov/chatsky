"""
Dataset
--------

This module contains data structures that are required to parse items from files
and parse requests and responses to and from various APIs.

"""
from pathlib import Path
import json
from typing import List, Dict, Union

from pydantic import BaseModel, Field, field_validator, model_validator

try:
    from yaml import load, SafeLoader

    pyyaml_available = True
except ImportError:
    pyyaml_available = False


class DatasetItem(BaseModel, arbitrary_types_allowed=True):
    """
    Data structure for storing labeled utterances.

    :param label: Raw classification label.
    :param samples: Utterance examples. At least one sentence is required.
    """

    label: str
    samples: List[Union[List[str], Dict[str, str], str]] = Field(default_factory=list, min_length=1)
    categorical_code: int = Field(default=0)


class Dataset(BaseModel, arbitrary_types_allowed=True):
    """
    Data structure for storing multiple :py:class:`~DatasetItem` objects.

    :param items: Can be initialized either with a list or with a dict
        of :py:class:`~DatasetItem` objects.
        Makes each item accessible by its label.
    """

    items: Dict[str, DatasetItem] = Field(default_factory=dict)
    flat_items: list = Field(default_factory=list)
    """`flat_items` field is populated automatically using objects from the `items` field."""

    def __getitem__(self, idx: str):
        return self.flat_items[idx]

    def __len__(self):
        return len(self.flat_items)

    @classmethod
    def _get_path(cls, file: str):
        if isinstance(file, Path):
            file_path = file
        else:
            file_path = Path(file)
        if not file_path.exists() or not file_path.is_file():
            raise OSError(f"File does not exist: {file}")
        return file_path

    @classmethod
    def parse_json(cls, file: Union[str, Path]):
        file_path = cls._get_path(file)
        items = json.load(file_path.open("r", encoding="utf-8"))
        return cls(items=[DatasetItem.model_validate(item) for item in items])

    @classmethod
    def parse_jsonl(cls, file: Union[str, Path]):
        file_path = cls._get_path(file)
        lines = file_path.open("r", encoding="utf-8").readlines()
        items = [DatasetItem.model_validate_json(line) for line in lines]
        return cls(items=items)

    @classmethod
    def parse_yaml(cls, file: Union[str, Path]):
        if not pyyaml_available:
            raise ImportError("`pyyaml` package missing. Try `pip install dff[ext].`")
        file_path = cls._get_path(file)
        raw_items = load(file_path.open("r", encoding="utf-8").read(), SafeLoader)["items"]
        items = [DatasetItem.model_validate(item) for item in raw_items]
        return cls(items=items)

    @field_validator("items", mode="before")
    @classmethod
    def pre_validate_items(cls, value: Union[Dict[str, DatasetItem], List[DatasetItem]]):
        if isinstance(value, list):  # if items were passed as a list, cast them to a dict
            new_value = [DatasetItem.model_validate(item) for item in value]
            item_labels = [item.label for item in new_value]
            value = {label: item for label, item in zip(item_labels, new_value)}

        return value

    # @root_validator
    @model_validator(mode="after")
    def post_validation(self):
        items: Dict[str, DatasetItem] = self.items
        for idx, key in enumerate(items.keys()):
            items[key].categorical_code = idx

        sentences = [sentence for dataset_item in items.values() for sentence in dataset_item.samples]
        pred_labels = [
            label for dataset_item in items.values() for label in [dataset_item.label] * len(dataset_item.samples)
        ]
        self.flat_items = list(zip(sentences, pred_labels))
        return self
