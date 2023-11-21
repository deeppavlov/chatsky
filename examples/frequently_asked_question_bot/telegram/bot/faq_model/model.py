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

with open(Path(__file__).parent / "faq_dataset_sample.json", "r", encoding="utf-8") as file:
    faq = json.load(file)


def find_similar_questions(question: str):
    """Return a list of similar questions from the database."""
    questions = list(map(lambda x: "<Q>" + x, faq.keys()))
    q_emb, *faq_emb = model.encode(["<Q>" + question] + questions)

    emb_with_scores = tuple(zip(questions, map(lambda x: np.linalg.norm(x - q_emb), faq_emb)))

    filtered_embeddings = tuple(sorted(filter(lambda x: x[1] < 10, emb_with_scores), key=lambda x: x[1]))

    result = []
    for question, score in filtered_embeddings:
        question = question.removeprefix("<Q>")
        result.append(question)
    return result
