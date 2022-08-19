import pathlib

from flask import Flask, request

from df_engine.core import Context, Actor

from df_db_connector import connector_factory
from .utils import run_actor, script

app = Flask(__name__)

pathlib.Path("dbs").mkdir(exist_ok=True)
db = connector_factory("json://dbs/file.json")

actor = Actor(script, start_label=("greeting_flow", "start_node"), fallback_label=("greeting_flow", "fallback_node"))


@app.route("/chat", methods=["GET", "POST"])
def respond():
    user_id = str(request.values.get("id"))
    user_message = str(request.values.get("message"))
    context = db.get(user_id, Context(id=user_id))

    context.add_request(user_message)
    updated_context = actor(context)
    response = updated_context.last_response

    updated_context.clear(hold_last_n_indexes=3)
    db[user_id] = updated_context
    return {"response": str(response)}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
