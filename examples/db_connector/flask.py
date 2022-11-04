"""
1. Flask
========
"""
import logging
import pathlib

from flask import Flask, request

from dff.core.engine.core import Actor, Context

from dff.connectors.db import connector_factory
from dff._example_utils.db_connector import run_auto_mode
from dff._example_utils.index import is_in_notebook, SCRIPT, run_actor

logger = logging.getLogger(__name__)

app = Flask(__name__)

pathlib.Path("dbs").mkdir(exist_ok=True)
db = connector_factory("json://dbs/file.json")

actor = Actor(SCRIPT, start_label=("greeting_flow", "start_node"), fallback_label=("greeting_flow", "fallback_node"))


@app.route("/chat", methods=["GET", "POST"])
def respond():
    user_id = str(request.values.get("id"))
    user_message = str(request.values.get("message"))
    ctx = db.get(user_id, Context(id=user_id))
    response, _ = run_actor(user_message, ctx, actor, logger=logger)
    return {"response": str(response)}


if __name__ == "__main__":
    if is_in_notebook():
        run_auto_mode(actor, db, logger)
    else:
        app.run(host="0.0.0.0", port=5000, debug=True)
