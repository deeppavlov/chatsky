from dff.script import Context


def generate_default_scheme(ctx: Context):
    result = dict()
    for key, value in ctx.items():
        if isinstance(value, list):
            enum_key = f"{key}[:]"
        elif isinstance(value, dict):
            enum_key = f"{key}[[:]]"
        else:
            enum_key = key
        result.update({enum_key: ["read", "hash_update"]})
    return result
