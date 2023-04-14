# %% [markdown]
"""
# 8. JSON storage with web API

This is a tutorial on using JSON with Flask.
"""


# %%
import pathlib

from dff.context_storages import context_storage_factory
from dff.script import Message
from dff.pipeline import Pipeline
from dff.utils.testing.common import check_happy_path, is_interactive_mode
from dff.utils.testing.toy_script import TOY_SCRIPT, HAPPY_PATH

from flask import Flask, request, jsonify


# %%
app = Flask(__name__)

pathlib.Path("dbs").mkdir(exist_ok=True)
db = context_storage_factory("json://dbs/file.json")


@app.route("/chat", methods=["GET", "POST"])
def respond():
    user_id = str(request.values.get("id"))
    user_message = str(request.values.get("message"))
    req = Message(text=user_message)
    context = pipeline(req, user_id)
    response = {"response": context.last_response.text}
    return jsonify(response)


# %%
pipeline = Pipeline.from_script(
    TOY_SCRIPT,
    context_storage=db,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
)


# %%
if __name__ == "__main__":
    # check_happy_path(pipeline, HAPPY_PATH)
    if is_interactive_mode():
        app.run(
            host="0.0.0.0", port=5000, debug=True
        )  # This runs tutorial in interactive mode (via flask, as a web server)
