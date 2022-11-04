from logging import Logger
from random import randint
from typing import Optional

from dff.connectors.db import DBConnector
from dff.core.engine.core import Actor, Context
from .index import TURNS, run_actor


def run_auto_mode(
    actor: Actor,
    db_connector: DBConnector,
    logger: Optional[Logger] = None,
    user_id: str = str(randint(0, 100)),
):
    for request, true_response in TURNS:
        ctx = db_connector.get(user_id, Context(id=user_id))
        response, ctx = run_actor(request, ctx, actor, true_response, logger=logger)
        db_connector[user_id] = response


def run_interactive_mode(
    actor: Actor,
    db_connector: DBConnector,
    logger: Optional[Logger] = None,
    user_id: str = str(randint(0, 100)),
):
    while True:
        request = input(">>> ")
        ctx = db_connector.get(user_id, Context(id=user_id))
        response, ctx = run_actor(request, ctx, actor, logger=logger)
        db_connector[user_id] = response
