"""
Simulation module for multi-arm scheduling.

Provides a unified :class:`SimulationInterface` with multiple backends:
- MockSimulator: software-only simulation (no GPU required)
- IsaacSimInterface: NVIDIA Isaac Sim backend
- OmniverseInterface: NVIDIA Omniverse Kit backend
- IsaacLabInterface: NVIDIA Isaac Lab backend (recommended for RL/eval)
"""

from simulation.arm_interface import ArmInterface, execute_generated_code
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
from simulation.isaac_lab import IsaacLabInterface
from simulation.isaac_sim import IsaacSimInterface
from simulation.mock_simulator import MockSimulator
from simulation.omniverse import OmniverseInterface
from simulation.scene_builder import SceneBuilder

__all__ = [
    "SimulationInterface",
    "SimulationState",
    "ArmState",
    "ArmStatus",
    "ObjectState",
    "ObjectStatus",
    "Position",
    "ActionResult",
    "MockSimulator",
    "IsaacSimInterface",
    "OmniverseInterface",
    "IsaacLabInterface",
    "SceneBuilder",
    "ArmInterface",
    "execute_generated_code",
]
