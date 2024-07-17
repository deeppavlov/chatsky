# flake8: noqa: F401

from chatsky.pipeline import Pipeline, Service, ServiceGroup, ComponentExtraHandler
from chatsky.pipeline.pipeline.actor import Actor
from chatsky.pipeline.pipeline.component import PipelineComponent
from chatsky.pipeline.types import ExtraHandlerRuntimeInfo
from chatsky.script import Context, Script

"""
Actor.model_rebuild()
PipelineComponent.model_rebuild()
ComponentExtraHandler.model_rebuild()
Pipeline.model_rebuild()
Service.model_rebuild()
ServiceGroup.model_rebuild()
"""
Pipeline.model_rebuild()
Script.model_rebuild()
Context.model_rebuild()
ExtraHandlerRuntimeInfo.model_rebuild()
