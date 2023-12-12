"""
ChatGPT
-------
This module defines functions for OpenAI API interaction.
"""
import os
import openai

CHATGPT_MAIN_PROMPT = """
Pretend that you are a member of staff for a book shop "Book Lovers Paradise".
Located at 123 Main Street.
Open seven days a week, from 9 AM to 9 PM.
Extensive collection of genres, including fiction, and non-fiction.
Knowledgeable staff. Online catalogue for easy browsing and ordering.
Comfortable seating areas and peaceful atmosphere.
Refund policy within 30 days of purchase.
Loyalty program for frequent customers (10% off purchases).
As a member of staff, you have access to information
outside of this description, e.g. you can make it up.
Don't mention your role in your replies, so that they seem natural.
"""

CHATGPT_QUESTION_PROMPT = """
What follows is a user query: answer it if you can do so
as a book shop's member of staff. If the query is unrelated to
your role, deny it.
"""

CHATGPT_COHERENCE_PROMPT = """
What follows is a question and an answer. Just write 'true' if the answer was satisfactory or 'false' otherwise.
"""

openai.api_key = os.getenv("OPENAI_API_TOKEN")


def get_output_factory():
    """
    Construct a get_output function encapsulating the execution counter.
    The function prompts ChatGPT for generated output.
    The main prompt is only included
    on the first invocation of the function.
    """

    def get_output_inner(request: str) -> str:
        messages = [
            {"role": "system", "content": CHATGPT_MAIN_PROMPT},
            {"role": "system", "content": CHATGPT_QUESTION_PROMPT},
            {"role": "user", "content": request},
        ]  # temporary fix until a better solution is found
        get_output_inner.num_calls += 1
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
        )
        return response["choices"][0]["message"]["content"]

    get_output_inner.num_calls = 0
    return get_output_inner


def get_coherence(request: str, response: str) -> str:
    """
    Prompt ChatGPT to evaluate the coherence of a request
    response pair.
    """
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": CHATGPT_COHERENCE_PROMPT},
            {"role": "user", "content": request},
            {"role": "assistant", "content": response},
        ],
    )
    return response["choices"][0]["message"]["content"]


get_output = get_output_factory()
