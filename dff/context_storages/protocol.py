"""
Protocol
--------
Base protocol code. Protocols :py:data:`.PROTOCOLS`.
A func is used for suggestion of installation: :py:func:`.get_protocol_install_suggestion`.
"""
import json
import pathlib

with open(pathlib.Path(__file__).parent / "protocols.json", "r", encoding="utf-8") as protocols:
    PROTOCOLS = json.load(protocols)
_prtocol_keys = {"module", "class", "slug", "uri_example"}
assert all(set(proc.keys()) == _prtocol_keys for proc in PROTOCOLS.values()), "Protocols are incomplete"


def get_protocol_install_suggestion(protocol_name: str) -> str:
    protocol = PROTOCOLS.get(protocol_name, {})
    slug = protocol.get("slug")
    if slug:
        return f"Try to run `pip install dff[{slug}]`"
    return ""
