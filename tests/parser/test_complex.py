from dff.utils.parser.dff_project import DFFProject


def test_referenced_object():
    dff_project = DFFProject.from_dict(
        {
            "main": {
                "proxy_1": "import proxy_1",
                "proxy_2": "import proxy_2",
                "nonexistent": "import mod",
                "other_nonexistent": "from module import object",
                "number": "proxy_1.prox.numbers[proxy_1.numbers.numbers[proxy_2.vars.lower_number]]"
                "[proxy_2.vars.number]",
                "object": "nonexistent._1._2",
                "other_object": "other_nonexistent._3._4",
                "value_nonexistent": "other_nonexistent[proxy_1.prox.numbers[1][2]]",
                "index_nonexistent": "proxy_2.numbers[object]",
                "second_index_nonexistent": "proxy_2.numbers[1][object]",
            },
            "proxy_1": {"prox": "import proxy_2", "numbers": "import other_variables"},
            "proxy_2": {
                "numbers": "from variables import dictionary",
                "vars": "import variables",
            },
            "variables": {
                "dictionary": "{1: {2: 3}}",
                "number": "2",
                "lower_number": "1",
            },
            "other_variables": {"numbers": "{1: 1, 2: 2}"},
        },
        validate=False,
    )

    assert dff_project["main"]["number"] == "3"
    assert dff_project["main"]["proxy_2"] == dff_project["proxy_2"]
    assert dff_project["main"]["nonexistent"] == "mod"
    assert dff_project["main"]["other_nonexistent"] == "module.object"
    assert dff_project["main"]["object"] == "mod._1._2"
    assert dff_project["main"]["other_object"] == "module.object._3._4"
    assert dff_project["main"]["value_nonexistent"] == "module.object[3]"
    assert dff_project["main"]["index_nonexistent"] == "{\n    1: {\n        2: 3,\n    },\n}[mod._1._2]"
    assert dff_project["main"]["second_index_nonexistent"] == "{\n    2: 3,\n}[mod._1._2]"
