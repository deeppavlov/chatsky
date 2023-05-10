# -*- coding: utf-8 -*-
# flake8: noqa: F401
"""
Parser Objects
--------------
This package defines parser objects.

Each class defined here is either an interface for other classes or represents a subset of :py:mod:`ast` classes.
The base interface for every parser object is :py:class:`~.BaseParserObject`.

Parser objects form a parser tree.
For example, an instance representing a statement `module.object = 6` is a node in the parser tree, and it has two
child nodes: `module.object` and `6`.
This tree structure allows to assign IDs to various objects (such as transition conditions) as a path to that object
from the tree root.
"""
from .base_classes import BaseParserObject, Expression, Statement, ReferenceObject, Python
from .expressions import String, Dict, Name, Attribute, Subscript, Iterable, Call, Comprehension
from .statements import Assignment, Import, ImportFrom
