"""
1. Flask
========
"""
import logging
import pathlib

from examples.utils import get_auto_arg
from flask import Flask, request

from dff.core.engine.core import Actor

from dff.connectors.db import connector_factory
from _db_connector_utils import script, run_actor, run_auto_mode

logger = logging.getLogger(__name__)

app = Flask(__name__)

pathlib.Path("dbs").mkdir(exist_ok=True)
db = connector_factory("json://dbs/file.json")

actor = Actor(script, start_label=("greeting_flow", "start_node"), fallback_label=("greeting_flow", "fallback_node"))


@app.route("/chat", methods=["GET", "POST"])
def respond():
    user_id = str(request.values.get("id"))
    user_message = str(request.values.get("message"))
    response, _ = run_actor(user_message, actor, db, logger, user_id)
    return {"response": str(response)}


if __name__ == "__main__":
    if get_auto_arg():
        run_auto_mode(actor, db, logger)
    else:
        app.run(host="0.0.0.0", port=5000, debug=True)
