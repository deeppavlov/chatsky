"""
Gensim Cosine Model
--------------------
This module provides an adapter interface for Gensim models.
Any embeddings from Gensim (e.g. Word2Vec, FastText or GLoVe) can be leveraged
to compute distances between utterances.
"""
from typing import Optional, Callable, List

try:
    import gensim
    import joblib

    gensim_available = True
    ALL_MODELS = [name for name in dir(gensim.models) if name[0].isupper()]  # all classes
except ImportError:
    joblib = object
    gensim_available = False
    ALL_MODELS = []

from dff.script.extras.conditions.models.base_model import ExtrasBaseModel
from dff.script.extras.conditions.dataset import Dataset
from dff.script.extras.conditions.utils import DefaultTokenizer
from dff.script.extras.conditions.models.local.cosine_matchers.cosine_matcher_mixin import CosineMatcherMixin


class GensimMatcher(CosineMatcherMixin, ExtrasBaseModel):
    """
    GensimMatcher utilizes embeddings from Gensim models to measure
    proximity between utterances and pre-defined labels.

    :param model: Gensim vector model (Word2Vec, FastText, etc.)
    :param dataset: Labels for the matcher. The prediction output depends on proximity to different labels.
    :param tokenizer: Class or function that performs string tokenization.
    :param namespace_key: Name of the namespace in framework states that the model will be using.
    :param kwargs: Keyword arguments are forwarded to the model constructor.
    """

    def __init__(
        self,
        model: object,
        dataset: Dataset,
        tokenizer: Optional[Callable[[str], List[str]]] = None,
        namespace_key: Optional[str] = None,
        **kwargs,
    ) -> None:
        if not gensim_available:
            raise ImportError("Required packages missing. Try `pip install dff[ext,gensim]`")
        CosineMatcherMixin.__init__(self, dataset=dataset)
        ExtrasBaseModel.__init__(self, namespace_key=namespace_key)
        self.model = model
        self.tokenizer = tokenizer or DefaultTokenizer()
        # self.fit(self.dataset, **kwargs)

    def transform(self, request: str):
        return self.model.wv.get_mean_vector(self.tokenizer(request)).reshape(1, -1)

    def fit(self, dataset: Dataset, **kwargs) -> None:
        """
        In case with GensimMatcher, using `fit` method implies that the model
        will be retrained and the previous state of the model will be discarded.
        The init arguments of the model are supposed to be passed as kwargs.
        """
        sentences, _ = map(list, zip(*dataset.flat_items))
        tokenized_sents = list(map(self.tokenizer, sentences))
        self.model = self.model.__class__(**kwargs)
        self.model.build_vocab(tokenized_sents)
        self.model.train(tokenized_sents, total_examples=self.model.corpus_count, epochs=self.model.epochs)

    def save(self, path: str):
        """
        Separately saves the model and the tokenizer to the specified path.
        `.model.bin` suffix is used to save the model.
        `.data.bin` suffix is used to save the dataset.
        `.tokenizer.bin` suffix is used for the tokenizer.

        :param path: Path to saving directory.
        """
        self.model.save(f"{path}.model.bin")
        joblib.dump(self.dataset, f"{path}.data.bin")
        joblib.dump(self.tokenizer, f"{path}.tokenizer.bin")

    @classmethod
    def load(cls, path: str, namespace_key: str) -> __qualname__:
        if not gensim_available:
            raise ImportError("`gensim` missing. Try `pip install dff[ext,gensim]`")
        with open(f"{path}.model.bin", "rb") as picklefile:
            contents = picklefile.readline()  # get the header line, find the class name inside
        for name in ALL_MODELS:
            if bytes(name, encoding="utf-8") in contents:
                model_cls: type = getattr(gensim.models, name)
                break
        else:
            raise ValueError(f"No matching model found for file {path}")

        model = model_cls.load(f"{path}.model.bin")
        dataset = joblib.load(f"{path}.data.bin")
        tokenizer = joblib.load(f"{path}.tokenizer.bin")
        return cls(model=model, tokenizer=tokenizer, dataset=dataset, namespace_key=namespace_key)
