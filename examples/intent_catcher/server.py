import logging
import time
import os
import random
import csv

import torch
import sentry_sdk
from flask import Flask, request, jsonify
from sentry_sdk.integrations.flask import FlaskIntegration
from transformers import DistilBertConfig, AutoModelForSequenceClassification, AutoTokenizer, pipeline


sentry_sdk.init(dsn=os.getenv("SENTRY_DSN"), integrations=[FlaskIntegration()])

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

random.seed(42)

DEFAULT_CONFIDENCE = 0.9
ZERO_CONFIDENCE = 0.0
MODEL_PATH = "model.pth.tar"
CLASSES_PATH = "classes.dict"

with open(CLASSES_PATH, "r") as file:
    reader = csv.reader(file, delimiter="\t")
    label2id = {line[0]: line[1] for line in reader}

id2label = {value: key for key, value in label2id.items()}

try:
    if torch.cuda.is_available():
        no_cuda = False
    else:
        no_cuda = True
    model = AutoModelForSequenceClassification.from_config(DistilBertConfig(num_labels=23))
    state = torch.load(MODEL_PATH, map_location = "cpu" if no_cuda else "gpu")
    model.load_state_dict(state["model_state_dict"])
    tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
    pipe = pipeline('text-classification', model=model, tokenizer=tokenizer)
    logger.info("predictor is ready")
except Exception as e:
    sentry_sdk.capture_exception(e)
    logger.exception(e)
    raise e

app = Flask(__name__)
logging.getLogger("werkzeug").setLevel("WARNING")


@app.route("/respond", methods=["POST"])
def respond():
    """
    The API expects a json object with the dialog history passed as an array and labeled 'dialog_contexts'.
    Intents will be extracted from the last utterance.

    .. code-block:: python
        {
            "dialog_contexts": ["phrase_1", "phrase_2"]
        }

    The API responds with a nested array containing 'label - score' pairs.

    .. code-block:: python
        [["definition",0.3393537402153015]]

    """
    st_time = time.time()
    contexts = request.json.get("dialog_contexts", [])

    try:
        results = pipe(contexts)
        indices = [int(''.join(filter(lambda x: x.isdigit(), result['label']))) for result in results]
        responses = [list(label2id.keys())[idx] for idx in indices]
        confidences = [result['score'] for result in results]
    except Exception as exc:
        logger.exception(exc)
        sentry_sdk.capture_exception(exc)
        responses = [""] * len(contexts)
        confidences = [ZERO_CONFIDENCE] * len(contexts)

    total_time = time.time() - st_time
    logger.info(f"Intent catcher exec time: {total_time:.3f}s")
    return jsonify(list(zip(responses, confidences)))
