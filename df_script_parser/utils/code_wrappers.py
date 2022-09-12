"""This module contains classes that wrap around python code represented as a string
to provide flexibility in how that python code should be displayed
"""
from abc import ABC
import typing as tp

from ruamel.yaml.constructor import Constructor
from ruamel.yaml.representer import Representer

from df_script_parser.utils.convenience_functions import enquote_string


class StringTag(ABC):
    """Abstract class for python code wrappers

    :param display_value: Value to be displayed
    :type display_value: str
    :param show_yaml_tag: Whether to add :py:attr:`StringTag.yaml_tag` to the :py:attr:`StringTag.display_value`,
        defaults to True
    :type show_yaml_tag: bool
    :param absolute_value: Absolute value. Used to check for equality of python objects,
        defaults to :py:attr:`StringTag.display_value`
    :type absolute_value: str
    :param display_absolute_value: Whether to display :py:attr:`StringTag.absolute_value` instead of
        :py:attr:`StringTag.display_value`, defaults to False
    :type display_absolute_value: bool
    """

    yaml_tag = "!tag"

    def __init__(
        self,
        display_value: str,
        show_yaml_tag: bool = True,
        absolute_value: tp.Union[str, None] = None,
        display_absolute_value: bool = False,
    ):
        self.display_value: str = display_value
        self.absolute_value: str = absolute_value if absolute_value else display_value
        self.show_yaml_tag: bool = show_yaml_tag
        self.display_absolute_value: bool = display_absolute_value

    def __str__(self):
        return self.display_value

    def __repr__(self):
        return self.display_value

    @classmethod
    def to_yaml(cls, representer: Representer, node: "StringTag"):
        """Represent object in yaml

        :param representer: Yaml node representer that provide functions for displaying values
        :type representer: :py:class:`ruamel.yaml.representer.Representer`
        :param node: Node that is represented
        :type node: :py:class:`StringTag`
        :return: Result of a method of ``representer``. The method and its arguments depend on attributes of ``node``:

            - If :py:attr:`node.show_yaml_tag` is set to True the method used is
              :py:meth:`ruamel.yaml.representer.Representer.represent_scalar`
              with the first parameter equal to :py:attr:`node.yaml_tag`
              else the method used is :py:meth:`ruamel.yaml.representer.Representer.represent_data`
            - If :py:attr:`node.display_absolute_value` is set to True
              the last parameter passed to the method is :py:attr:`node.absolute_value` else it is
              :py:attr:`node.display_value`

        :rtype: Any
        """
        if node.display_absolute_value:
            value = node.absolute_value
        else:
            value = node.display_value
        if node.show_yaml_tag:
            return representer.represent_scalar(cls.yaml_tag, value)
        return representer.represent_data(value)

    @classmethod
    def from_yaml(cls, constructor: Constructor, node):  # pylint: disable=unused-argument
        """Construct the class from yaml

        :param constructor: Yaml constructor of a class
        :type constructor: :py:class:`.Constructor`
        :param node: Yaml node
        :return: Instance of the class
        """
        return cls(node.value)


class String(StringTag):
    """This class is used to represent string.

    Overrides :py:meth:`StringTag.__repr__` to enquote its result
    """

    yaml_tag = "!str"

    def __hash__(self):
        return hash(self.absolute_value)

    def __eq__(self, other):
        if isinstance(other, String):
            return self.absolute_value == other.absolute_value
        return False

    def __repr__(self):
        return enquote_string(super().__repr__())


class Python(StringTag):
    """This class is used to represent python code including references to python objects.

    - :py:attr:`StringTag.absolute_value` is used to refer to the object
    - :py:attr:`StringTag.show_yaml_tag` is set to False by default
    - :py:attr:`StringTag.display_absolute_value` is set to False by default

    :param display_value: Value to be displayed
    :type display_value: str
    :param absolute_value: Absolute value. Used to check for equality of python objects,
        defaults to :py:attr:`StringTag.display_value`
    :type absolute_value: str
    :param show_yaml_tag: Whether to add :py:attr:`StringTag.yaml_tag` to the :py:attr:`StringTag.display_value`,
        defaults to True
    :type show_yaml_tag: bool
    :param display_absolute_value: Whether to display :py:attr:`StringTag.absolute_value` instead of
        :py:attr:`StringTag.display_value`, defaults to False
    :type display_absolute_value: bool
    """

    yaml_tag = "!py"

    def __init__(
        self,
        display_value: str,
        absolute_value: tp.Union[str, None] = None,
        show_yaml_tag: bool = False,
        display_absolute_value: bool = False,
    ):
        super().__init__(display_value, show_yaml_tag, absolute_value, display_absolute_value)

    def __hash__(self):
        return hash(self.absolute_value)

    def __eq__(self, other):
        if isinstance(other, Python):
            return self.absolute_value == other.absolute_value
        return False
