"""
Types
******

This module contains structures that are required to parse items from files
and parse requests and responses to and from various APIs.

"""
from pathlib import Path
from typing import List, Dict, Union

from pydantic import BaseModel, Field, PrivateAttr, parse_file_as, parse_obj_as, validator, root_validator
try:
    from yaml import load
    pyyaml_available = True
except ImportError:
    pyyaml_available = False

try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader


class DatasetItem(BaseModel):
    label: str
    samples: List[Union[List[str], Dict[str, str], str]] = Field(default_factory=list, min_items=1)
    _categorical_code = PrivateAttr(default=0)


class Dataset(BaseModel):
    items: Dict[str, DatasetItem] = Field(default_factory=dict)
    flat_items: list = Field(default_factory=list)

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
    def parse_json(cls, file: Union[str, Path]) -> None:
        file_path = cls._get_path(file)
        items = parse_file_as(List[DatasetItem], file_path)
        return cls(items=items)

    @classmethod
    def parse_jsonl(cls, file: Union[str, Path]) -> None:
        file_path = cls._get_path(file)
        lines = file_path.open("r", encoding="utf-8").readlines()
        items = [DatasetItem.parse_raw(line) for line in lines]
        return cls(items=items)

    @classmethod
    def parse_yaml(cls, file: Union[str, Path]) -> None:
        if not pyyaml_available:
            raise ImportError("`pyyaml` package missing. Try `pip install dff[ext].`")
        file_path = cls._get_path(file)
        raw_intents = load(file_path.open("r", encoding="utf-8").read(), SafeLoader)["items"]
        items = parse_obj_as(List[DatasetItem], raw_intents)
        return cls(items=items)

    @validator("items", pre=True)
    def pre_validate_items(cls, value: Union[Dict[str, DatasetItem], List[DatasetItem]]):
        if isinstance(value, list):  # if items were passed as a list, cast them to a dict
            item_labels = [item.label for item in value]
            return {label: item for label, item in zip(item_labels, value)}
        return value

    @validator("items")
    def validate_items(cls, value: Dict[str, DatasetItem]):
        for idx, key in enumerate(value.keys()):
            value[key]._categorical_code = idx
        return value

    @root_validator
    def validate_flat_items(cls, values: dict):
        items: Dict[str, DatasetItem] = values.get("items")
        sentences = [sentence for dataset_item in items.values() for sentence in dataset_item.samples]
        pred_labels = [
            label for dataset_item in items.values() for label in [dataset_item.label] * len(dataset_item.samples)
        ]
        values["flat_items"] = list(zip(sentences, pred_labels))
        return values
