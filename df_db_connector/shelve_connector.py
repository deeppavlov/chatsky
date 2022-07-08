"""
shelve_connector
---------------------------
Provides the shelve-based version of the :py:class:`~df_db.connector.db_connector.DBConnector`.
"""
import os
import pickle
from shelve import DbfilenameShelf

from .db_connector import DBConnector


class ShelveConnector(DbfilenameShelf, DBConnector):
    """
    Implements :py:class:`~df_db.connector.db_connector.DBConnector` with `shelve` as the driver.

    Parameters
    -----------

    path: str
        Target file URI. Example: `shelve://file.db`
    """

    def __init__(self, path: str):
        DBConnector.__init__(self, path)

        DbfilenameShelf.__init__(self, filename=self.path, protocol=pickle.HIGHEST_PROTOCOL)

    def __del__(self):
        self.close()
