"""
Abstract simulation interface for multi-arm scheduling.

Defines the base classes and data structures that all simulator
implementations must conform to.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ArmStatus(Enum):
    """Status of a robot arm."""

    IDLE = "idle"
    MOVING = "moving"
    EXECUTING = "executing"
    ERROR = "error"


class ObjectStatus(Enum):
    """Status of an object in the scene."""

    IDLE = "idle"
    GRASPED = "grasped"
    PLACED = "placed"
    IN_TRANSIT = "in_transit"
    DONE = "done"


@dataclass
class Position:
    """3D position with optional orientation."""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0

    def as_dict(self) -> Dict[str, float]:
        return {
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "roll": self.roll,
            "pitch": self.pitch,
            "yaw": self.yaw,
        }

    def distance_to(self, other: "Position") -> float:
        return (
            (self.x - other.x) ** 2 + (self.y - other.y) ** 2 + (self.z - other.z) ** 2
        ) ** 0.5


@dataclass
class ArmState:
    """State of a single robot arm."""

    arm_id: str
    status: ArmStatus = ArmStatus.IDLE
    position: Position = field(default_factory=Position)
    gripper_open: bool = True
    current_task: Optional[str] = None
    held_object: Optional[str] = None
    joint_angles: Dict[str, float] = field(default_factory=dict)


@dataclass
class ObjectState:
    """State of an object in the simulation."""

    object_id: str
    object_type: str
    position: Position = field(default_factory=Position)
    status: ObjectStatus = ObjectStatus.IDLE
    held_by: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionResult:
    """Result of executing an action in the simulation."""

    success: bool
    duration: float
    position: Optional[Position] = None
    error_message: Optional[str] = None
    sensor_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SimulationState:
    """Complete state of the simulation at a point in time."""

    timestamp: float
    arm_states: Dict[str, ArmState] = field(default_factory=dict)
    object_states: Dict[str, ObjectState] = field(default_factory=dict)
    is_running: bool = False


class SimulationInterface(ABC):
    """
    Abstract base class for simulation backends.

    All simulator implementations (mock, Isaac Sim, etc.) must implement
    this interface to ensure consistent behavior across environments.
    """

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the simulation environment."""
        ...

    @abstractmethod
    def load_scene(self, scene_config: dict) -> None:
        """
        Load a scene from a configuration dictionary.

        Args:
            scene_config: Dictionary describing the scene layout including
                         workstations, conveyors, workpieces, and robot arms.
        """
        ...

    @abstractmethod
    def execute_action(self, arm_id: str, action: dict) -> ActionResult:
        """
        Execute an action with a specific robot arm.

        Args:
            arm_id: ID of the robot arm to execute the action.
            action: Dictionary describing the action, e.g.
                    {"type": "pick", "target": "workpiece_001", "position": {...}}

        Returns:
            ActionResult with success status, duration, and sensor data.
        """
        ...

    @abstractmethod
    def get_state(self) -> SimulationState:
        """
        Get the current simulation state.

        Returns:
            SimulationState containing all arm and object states.
        """
        ...

    @abstractmethod
    def step(self) -> None:
        """Advance the simulation by one time step."""
        ...

    @abstractmethod
    def reset(self) -> None:
        """Reset the simulation to its initial state."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Shut down the simulation and release resources."""
        ...
