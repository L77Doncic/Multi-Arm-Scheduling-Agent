"""
Simulation package for multi-arm scheduling.

Exports
-------
Core types:
    SimulationInterface, ActionResult, SimulationState
    ArmState, ArmStatus, ObjectState, ObjectStatus, Position

Implementations:
    MockSimulator, IsaacSimInterface

Scene construction:
    SceneBuilder, Scene, Workstation, Conveyor, Workpiece, RobotArm, Bounds
"""

from simulation.base import (
    ActionResult,
    ArmState,
    ArmStatus,
    ObjectState,
    ObjectStatus,
    Position,
    SimulationInterface,
    SimulationState,
)
from simulation.isaac_sim import IsaacSimInterface
from simulation.mock_simulator import MockSimulator
from simulation.scene_builder import (
    Bounds,
    Conveyor,
    RobotArm,
    Scene,
    SceneBuilder,
    Workpiece,
    Workstation,
)

__all__ = [
    # base
    "SimulationInterface",
    "ActionResult",
    "SimulationState",
    "ArmState",
    "ArmStatus",
    "ObjectState",
    "ObjectStatus",
    "Position",
    # implementations
    "MockSimulator",
    "IsaacSimInterface",
    # scene
    "SceneBuilder",
    "Scene",
    "Workstation",
    "Conveyor",
    "Workpiece",
    "RobotArm",
    "Bounds",
]
