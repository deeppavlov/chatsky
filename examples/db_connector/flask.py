"""
1. Flask
========
"""
import logging
import pathlib

from flask import Flask, request

from dff.connectors.db import connector_factory
from dff.utils.common import create_example_pipeline, is_in_notebook

logger = logging.getLogger(__name__)

app = Flask(__name__)

pathlib.Path("dbs").mkdir(exist_ok=True)
db = connector_factory("json://dbs/file.json")

pipeline = create_example_pipeline(logger, context_storage=db)


@app.route("/chat", methods=["GET", "POST"])
def respond():
    user_id = str(request.values.get("id"))
    user_message = str(request.values.get("message"))
    context = pipeline(user_message, user_id)
    return {"response": str(context.last_response)}


if __name__ == "__main__":
    if is_in_notebook():
        pipeline.run()
    else:
        app.run(host="0.0.0.0", port=5000, debug=True)
