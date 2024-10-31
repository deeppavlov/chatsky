import re


# Filter func for building latest versions of each major tag.
# Returns a dictionary of major tag groups as keys and latest tag's number as values
# e.g. {(0, 6): 7, (1, 2): 3} standing for v0.6.7 and v1.2.3.
def latest_tags_filter(tag_list: list) -> list:
    regex = re.compile(r"^v\d*\.\d*\.\d*$")
    tag_list = list(filter(regex.match, tag_list))
    latest_tags = {}
    for tag in tag_list:
        tag = str(tag).replace("v", "").split(".")
        tag_group = (tag[0], tag[1])
        # Not building versions lower than v0.8.0
        if not (int(tag[0]) == 0 and int(tag[1]) < 8):
            # If there is a greater tag in this group, it will have priority over others
            if int(tag[2]) > int(latest_tags.get(tag_group, -1)):
                latest_tags[tag_group] = tag[2]
    # Could return a dictionary, but it looks unclear.
    tag_list = ["v" + x[0] + "." + x[1] + "." + latest_tags[x] for x in latest_tags.keys()]
    return tag_list
