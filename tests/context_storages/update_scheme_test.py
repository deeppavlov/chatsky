from dff.context_storages import UpdateScheme
from dff.script import Context

default_update_scheme = {
    "id": ["read", "update"],
    "requests[-1]": ["read", "append"],
    "responses[-1]": ["read", "append"],
    "labels[-1]": ["read", "append"],
    "misc[[all]]": ["read", "hash_update"],
    "framework_states[[all]]": ["read", "hash_update"],
}

full_update_scheme = {
    "id": ["read", "update"],
    "requests[:]": ["read", "append"],
    "responses[:]": ["read", "append"],
    "labels[:]": ["read", "append"],
    "misc[[all]]": ["read", "update"],
    "framework_states[[all]]": ["read", "update"],
}


def test_default_scheme_creation():
    print()

    default_scheme = UpdateScheme(default_update_scheme)
    print(default_scheme.__dict__)

    full_scheme = UpdateScheme(full_update_scheme)
    print(full_scheme.__dict__)

    out_ctx = Context()
    print(out_ctx.dict())

    mid_ctx = default_scheme.process_context_write(out_ctx, dict())
    print(mid_ctx)

    context = default_scheme.process_context_read(mid_ctx)
    print(context.dict())
