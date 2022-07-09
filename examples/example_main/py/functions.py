from df_engine.core import Actor, Context


def add_prefix(prefix):
    def add_prefix_processing(ctx: Context, actor: Actor, *args, **kwargs) -> Context:
        processed_node = ctx.a_s.get("processed_node", ctx.a_s["next_node"])
        processed_node.response = f"{prefix}: {processed_node.response}"
        ctx.a_s["processed_node"] = processed_node
        return ctx

    return add_prefix_processing
