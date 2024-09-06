from pathlib import Path

import pytest

import chatsky
from chatsky.core.script_parsing import JSONImporter, JSONImportError


current_dir = Path(__file__).parent.absolute()


class TestResolveStringReference:
    @pytest.mark.parametrize(
        "string",
        [
            "custom.V",
            "custom.sub.VAR",
            "custom.sub.sub.V",
            "custom.sub.sub.f.VAR",
            "custom.submodule.VAR",
            "custom.submodule.sub.V",
            "custom.submodule.sub.f.VAR",
            "custom.submodule.submodule.V",
            "custom.submodule.submodule.f.VAR",
            "custom.submodule.submodule.file.VAR",
            "custom.sub.submodule.V",
            "custom.sub.submodule.f.VAR",
            "custom.sub.submodule.file.VAR",
        ],
    )
    def test_resolve_custom_object(self, string):
        json_importer = JSONImporter(custom_dir=current_dir / "custom")

        assert json_importer.resolve_string_reference(string) == 1

    def test_different_custom_location(self):
        json_importer = JSONImporter(custom_dir=current_dir / "custom_dir")

        assert json_importer.resolve_string_reference("custom.VAR") == 2
        assert json_importer.resolve_string_reference("custom.module.VAR") == 3

    @pytest.mark.parametrize(
        "obj,val",
        [
            ("chatsky.cnd.ExactMatch", chatsky.conditions.ExactMatch),
            ("chatsky.conditions.standard.ExactMatch", chatsky.conditions.ExactMatch),
            ("chatsky.core.message.Image", chatsky.core.message.Image),
            ("chatsky.Message", chatsky.Message),
            ("chatsky.context_storages.sql.SQLContextStorage", chatsky.context_storages.sql.SQLContextStorage),
            ("chatsky.messengers.telegram.LongpollingInterface", chatsky.messengers.telegram.LongpollingInterface),
            ("chatsky.stats.cli.DASHBOARD_SLUG", "chatsky-stats"),
            ("chatsky.stats.utils.SERVICE_NAME", "chatsky"),
        ],
    )
    def test_resolve_chatsky_objects(self, obj, val):
        json_importer = JSONImporter(custom_dir=current_dir / "none")

        assert json_importer.resolve_string_reference(obj) == val

    def test_non_existent_custom_dir(self):
        json_importer = JSONImporter(custom_dir=current_dir / "none")
        with pytest.raises(JSONImportError, match="Could not find directory"):
            json_importer.resolve_string_reference("custom.VAR")

    def test_wrong_prefix(self):
        json_importer = JSONImporter(custom_dir=current_dir / "none")
        with pytest.raises(JSONImportError):
            json_importer.resolve_string_reference("wrong_domain.VAR")

    def test_non_existent_object(self):
        json_importer = JSONImporter(custom_dir=current_dir / "custom_dir")
        with pytest.raises(JSONImportError, match="Could not import"):
            json_importer.resolve_string_reference("chatsky.none.VAR")
        with pytest.raises(JSONImportError, match="Could not import"):
            json_importer.resolve_string_reference("custom.none.VAR")


@pytest.mark.parametrize(
    "obj,replaced",
    [
        (5, 5),
        (True, True),
        ("string", "string"),
        ("custom.V", 1),
        ("chatsky.stats.utils.SERVICE_NAME", "chatsky"),
        ({"text": "custom.V"}, {"text": 1}),
        ({"1": {"2": "custom.V"}}, {"1": {"2": 1}}),
        ({"1": "custom.V", "2": "custom.V"}, {"1": 1, "2": 1}),
        (["custom.V", 4], [1, 4]),
        ({"chatsky.Message": None}, chatsky.Message()),
        ({"chatsky.Message": ["text"]}, chatsky.Message("text")),
        ({"chatsky.Message": {"text": "text", "misc": {}}}, chatsky.Message("text", misc={})),
        ({"chatsky.Message": ["chatsky.stats.utils.SERVICE_NAME"]}, chatsky.Message("chatsky")),
    ],
)
def test_replace_resolvable_objects(obj, replaced):
    json_importer = JSONImporter(custom_dir=current_dir / "custom")

    assert json_importer.replace_resolvable_objects(obj) == replaced


class TestImportPipelineFile:
    def test_normal_import(self):
        pipeline = chatsky.Pipeline.from_file(
            current_dir / "pipeline.yaml",
            custom_code_directory=current_dir / "custom",
            fallback_label=("flow", "node"),  # override the parameter
        )

        assert pipeline.start_label.node_name == "node"
        assert pipeline.fallback_label.node_name == "node"
        start_node = pipeline.script.get_node(pipeline.start_label)
        assert start_node.response.root == chatsky.Message("hi", misc={"key": 1})
        assert start_node.transitions[0].dst == chatsky.dst.Previous()
        assert start_node.transitions[0].cnd == chatsky.cnd.HasText("t")

        assert pipeline.slots.person.likes == chatsky.slots.RegexpSlot(regexp="I like (.+)", match_group_idx=1)
        assert pipeline.slots.person.age == chatsky.slots.RegexpSlot(regexp="I'm ([0-9]+) years old", match_group_idx=1)

    def test_import_json(self):
        pipeline = chatsky.Pipeline.from_file(
            current_dir / "pipeline.json", custom_code_directory=current_dir / "custom"
        )

        assert pipeline.script.get_node(pipeline.start_label).misc == {"key": 1}

    def test_wrong_file_ext(self):
        with pytest.raises(JSONImportError, match="extension"):
            chatsky.Pipeline.from_file(current_dir / "__init__.py")

    def test_wrong_object_type(self):
        with pytest.raises(JSONImportError, match="dict"):
            chatsky.Pipeline.from_file(current_dir / "wrong_type.json")
