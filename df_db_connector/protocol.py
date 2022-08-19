"""
protocol
---------------------------
| Base protocol code.
| Protocols :py:data:`~df_db_connector.protocol.PROTOCOLS`.
| A function is used for suggestion of installation: :py:func:`~df_db_connector.protocol.get_protocol_install_suggestion`

"""
import json
import pathlib

PROTOCOLS = json.load((pathlib.Path(__file__).parent / "protocols.json").open())
_prtocol_keys = {"module", "class", "slug", "extras_require", "uri_example"}
assert all(set(proc.keys()) == _prtocol_keys for proc in PROTOCOLS.values()), "Protocols are uncomplite"


def get_protocol_install_suggestion(protocol_name: str) -> str:
    protocol = PROTOCOLS.get(protocol_name, {})
    slug = protocol.get("slug")
    if slug and protocol.get("extras_require"):
        return f"Try to run `pip install df_db_connector[{slug}]`"
    return ""
