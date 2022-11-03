from sklearn.metrics.pairwise import cosine_similarity
from argparse import Namespace

try:
    import numpy as np

    IMPORT_ERROR_MESSAGE = None
except ImportError as e:
    np = Namespace(ndarray=None)
    IMPORT_ERROR_MESSAGE = e.msg


from ....dataset import Dataset


class CosineMatcherMixin:
    """
    This class imlements a 'predict' method that returns the likelihood of each label
    from a pre-defined collection, judging by how close the last request is to the examples.

    Parameters
    -----------
    dataset: Dataset
        Labels for the matcher. The prediction output depends on proximity to examples of different labels.
    """

    def __init__(self, dataset: Dataset):
        self.dataset = dataset

    def predict(self, request: str) -> dict:
        request_cls_embedding = self.transform(request)
        result = dict()
        for label_name, dataset_item in self.dataset.items.items():
            reference_examples = dataset_item.samples
            reference_embeddings = [self.transform(item) for item in reference_examples]
            cosine_scores = [
                cosine_similarity(request_cls_embedding, ref_emb)[0][0] for ref_emb in reference_embeddings
            ]
            result[label_name] = np.max(np.array(cosine_scores))

        return result
