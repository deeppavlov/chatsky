# %% [markdown]
# Web API: 4. Streamlit chat interface
"""
This tutorial shows how to use an API endpoint that we created in the FastAPI tutorial
in a Streamlit chat.

A demonstration of the chat:
![demo](https://user-images.githubusercontent.com/61429541/238721597-ef88261d-e9e6-497d-ba68-0bcc9a765808.png)

<div class="alert alert-{primary/secondary/success/danger/warning/info/light/dark}">
Note! You will need an API running to test this tutorial.
You can run Web API Interface from tutorial 1 using this command:
```bash
python model.py
```
Make sure that ports you specify in `API_URL` here are the same as in your API file (e.g. 8000). 
</div>

"""
# %pip install dff streamlit streamlit-chat

# %% [markdown]
# ## Module and package import


# %%
###########################################################
# This patch is only needed to import Message from dff.
# Streamlit Chat interface can be written without using it.
import asyncio

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
###########################################################


# %%
import uuid
import itertools

import requests
import streamlit as st
import streamlit.components.v1 as components
from dff.script import Message


# %% [markdown]
# ## API configuration
#
# Here we define methods to contact the API endpoint.


# %%
API_URL = "http://localhost:8000/chat"


def query(payload, user_id) -> requests.Response:
    response = requests.post(
        API_URL + f"?user_id={user_id}",
        headers={
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json=payload,
    )
    return response


# %% [markdown]
# ## Streamlit configuration
#
# Here we configure Streamlit page and initialize some session variables:
#
# 1. `user_id` -- stores user_id to be used in pipeline.
# 2. `bot_responses` -- a list of bot responses.
# 3. `user_requests` -- a list of user requests.


# %%
st.set_page_config(page_title="Streamlit DFF Chat", page_icon=":robot:")

st.header("Streamlit DFF Chat")

if "user_id" not in st.session_state:
    st.session_state["user_id"] = str(uuid.uuid4())

if "bot_responses" not in st.session_state:
    st.session_state["bot_responses"] = []

if "user_requests" not in st.session_state:
    st.session_state["user_requests"] = []


# %% [markdown]
# ## UI setup
#
# Here we configure elements that will be used in Streamlit to interact with the API.
#
# First we define a text input field which a user is supposed to type his requests into.
# Then we define a button that sends a query to the API, logs requests and responses,
# and clears the text field.


# %%
def get_bot_response(user_request: str):
    """
    Get request from user as an argument. Receive response from API endpoint.

    Ensure that request is not empty.
    Add both the request and response to `user_requests` and `bot_responses`.
    """

    if user_request == "":
        return

    st.session_state["user_requests"].append(user_request)

    bot_response = query(
        Message(text=user_request).model_dump(),
        user_id=st.session_state["user_id"],
    )
    bot_response.raise_for_status()

    bot_message = Message.model_validate(bot_response.json()["response"]).text

    # # Implementation without using Message:
    # bot_response = query(
    #     {"text": user_request},
    #     user_id=st.session_state["user_id"]
    # )
    # bot_response.raise_for_status()
    #
    # bot_message = bot_response.json()["response"]["text"]

    st.session_state["bot_responses"].append(bot_message)

    st.session_state["input"] = ""


# %%
if prompt := st.chat_input("Enter your message"):
    get_bot_response(prompt)


# %% [markdown]
# ### Component patch
#
# Here we add a component that presses the `Send` button whenever user presses the `Enter` key.


# %%
components.html(
    """
<script>
const doc = window.parent.document;
buttons = Array.from(doc.querySelectorAll('button[kind=secondary]'));
const send_button = buttons.find(el => el.innerText === 'Send');
doc.addEventListener('keypress', function(e) {
    switch (e.keyCode) {
        case 13: // (13 = Enter key)
            send_button.click();
            break;
    }
});
</script>
""",
    height=0,
    width=0,
)


# %% [markdown]
# ### Message display
#
# Here we use the `st.chat_message` to display user requests and bot responses.


# %%
for i, bot_response, user_request in zip(
    itertools.count(0),
    st.session_state.get("bot_responses", []),
    st.session_state.get("user_requests", []),
):
    with st.chat_message("user"):
        st.markdown(user_request)
    with st.chat_message("ai"):
        st.markdown(bot_response)

# %% [markdown]
# ## Running Streamlit:
#
# ```bash
# streamlit run {file_name}
# ```