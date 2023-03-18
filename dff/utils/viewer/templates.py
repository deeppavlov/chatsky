from jinja2 import Template

NAME_TEMPLATE = Template(
    """
    <tr>
        <td> <br align="left" /></td>
        <td><b>{{ name_value | upper | replace("'", "") }}</b></td>
        <td> <br align="right" /></td>
    </tr>
    """
)

TITLE_TEMPLATE = Template(
    """
    <hr/>
    <tr>
        <td><br align="left" /> <br align="left" /></td>
        <td><b>{{ title }}</b></td>
        <td> <br align="right" /></td>
    </tr>
    """
)

LINES_TEMPLATE = Template(
    """
    <tr>
        <td> <br align="left" /></td>
        <td>{% for line in lines %}{{ line | escape }}<br/>{% endfor %}</td>
        <td> <br align="right" /></td>
    </tr>
    """
)

PORT_TEMPLATE = Template(
    """
    <tr>
        <td>(<br align="left" /></td>
        <td>{{ name }}</td>
        <td port="{{ port }}">)<br align="right" /></td>
    </tr>
    """
)

TABLE_TEMPLATE = Template(
    """
    <<table border="0" cellborder="0" cellspacing="6" cellpadding="0">
        {% for row in rows %}
        {{ row }}
        {% endfor %}
    </table>>
    """
)