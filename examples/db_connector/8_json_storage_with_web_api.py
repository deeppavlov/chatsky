# %% [markdown]
"""
# 8. JSON storage with web API

This is an example of using JSON with web API.
"""


# %%
import pathlib

from dff.core.pipeline import Pipeline
from dff.utils.testing.common import check_happy_path, is_interactive_mode
from dff.utils.testing.toy_script import TOY_SCRIPT, HAPPY_PATH

from flask import Flask, request

from dff.connectors.db import connector_factory


# %%
app = Flask(__name__)

pathlib.Path("dbs").mkdir(exist_ok=True)
db = connector_factory("json://dbs/file.json")


@app.route("/chat", methods=["GET", "POST"])
def respond():
    user_id = str(request.values.get("id"))
    user_message = str(request.values.get("message"))
    context = pipeline(user_message, user_id)
    return {"response": str(context.last_response)}


# %%
pipeline = Pipeline.from_script(
    TOY_SCRIPT,
    context_storage=db,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
)


# %%
if __name__ == "__main__":
    check_happy_path(pipeline, HAPPY_PATH)
    if is_interactive_mode():
        app.run(
            host="0.0.0.0", port=5000, debug=True
        )  # This runs example in interactive mode (via flask, as a web server)
