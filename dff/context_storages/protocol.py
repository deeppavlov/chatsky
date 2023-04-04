"""
Protocol
--------
The Protocol module contains the base code for the different communication protocols used in the DFF.
It defines the :py:data:`.PROTOCOLS` constant, which lists all the supported protocols in the DFF.

The module also includes a function :py:func:`.get_protocol_install_suggestion()` that is used to provide
suggestions for installing the necessary dependencies for a specific protocol.
This function takes the name of the desired protocol as an argument and returns
a string containing the necessary installation commands for that protocol.

The DFF supports a variety of communication protocols,
which allows it to communicate with different types of databases.
"""
import json
import pathlib

with open(pathlib.Path(__file__).parent / "protocols.json", "r", encoding="utf-8") as protocols:
    PROTOCOLS = json.load(protocols)
_prtocol_keys = {"module", "class", "slug", "uri_example"}
assert all(set(proc.keys()) == _prtocol_keys for proc in PROTOCOLS.values()), "Protocols are incomplete"


def get_protocol_install_suggestion(protocol_name: str) -> str:
    """
    Provide suggestions for installing the necessary dependencies for a specific protocol.

    :param protocol_name: Protocol name.
    """
    protocol = PROTOCOLS.get(protocol_name, {})
    slug = protocol.get("slug")
    if slug:
        return f"Try to run `pip install dff[{slug}]`"
    return ""
