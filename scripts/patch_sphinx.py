from wrapt import wrap_function_wrapper, register_post_import_hook


def _extract_summary_wrapper(wrapped, instance, args, kwargs):
    return wrapped(*args, **kwargs).split("\n\n")[-1]


def _depart_gallery_html_wrapper(wrapped, instance, args, kwargs):
    def _extract_node(_, node, *__, **___):
        return node

    node_arg = _extract_node(*args, **kwargs)

    entries = node_arg["entries"]
    for i in range(len(entries)):
        entries[i] = list(entries[i])
        title_split = entries[i][0].split(": ")
        entries[i][0] = entries[i][0] if len(title_split) == 1 else title_split[-1]

    return wrapped(*args, **kwargs)


def patch_autosummary(module):
    print("patching", module.__name__)
    wrap_function_wrapper(module, "extract_summary", _extract_summary_wrapper)


def patch_nbsphinx(module):
    print("patching", module.__name__)
    wrap_function_wrapper(module, "depart_gallery_html", _depart_gallery_html_wrapper)


register_post_import_hook(patch_autosummary, "sphinx.ext.autosummary")
register_post_import_hook(patch_nbsphinx, "nbsphinx")
