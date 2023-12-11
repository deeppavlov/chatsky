"""
Model
-----
This module defines AI-dependent functions.
"""
import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("clips/mfaq")

with open(Path(__file__).parent / "request_translations.json", "r", encoding="utf-8") as file:
    request_translations = json.load(file)

with open(Path(__file__).parent / "response_translations.json", "r", encoding="utf-8") as file:
    response_translations = json.load(file)

with open(Path(__file__).parent / "faq_dataset_sample.json", "r", encoding="utf-8") as file:
    faq = json.load(file)


def find_similar_question(question: str, lang: str) -> str | None:
    """Return the most similar question from the faq database."""
    questions = list(map(lambda x: "<Q>" + x, request_translations[lang]))
    q_emb, *faq_emb = model.encode(["<Q>" + question] + questions)

    scores = list(map(lambda x: np.linalg.norm(x - q_emb), faq_emb))

    argmin = scores.index(min(scores))
    if argmin < 5:
        return list(faq.keys())[argmin]
    return None
