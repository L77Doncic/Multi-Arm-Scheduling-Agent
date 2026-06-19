"""
Mock simulator for testing without Isaac Sim.

Provides a software-only simulation of robot arm operations including
pick, place, move, assemble, and inspect actions with configurable
failure probabilities and full execution tracing.
"""

import logging
import math
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

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

logger = logging.getLogger(__name__)


# Default operation durations (seconds)
DEFAULT_DURATIONS: Dict[str, float] = {
    "pick": 1.5,
    "place": 1.5,
    "move": 2.0,
    "assemble": 4.0,
    "inspect": 2.5,
}

# Default failure probabilities per action type
DEFAULT_FAILURE_PROBS: Dict[str, float] = {
    "pick": 0.05,
    "place": 0.03,
    "move": 0.02,
    "assemble": 0.08,
    "inspect": 0.04,
}


@dataclass
class TraceEntry:
    """Single entry in the execution trace."""
    timestamp: float
    arm_id: str
    action: Dict[str, Any]
    result: ActionResult


class MockSimulator(SimulationInterface):
    """
    Software-only simulator for multi-arm scheduling.

    Simulates robot arm operations with realistic timing, configurable
    failure probabilities, and complete execution tracing.  Useful for
    unit tests, rapid prototyping, and CI pipelines where a physics
    engine is unavailable.
    """

    def __init__(
        self,
        failure_probabilities: Optional[Dict[str, float]] = None,
        action_durations: Optional[Dict[str, float]] = None,
        time_scale: float = 1.0,
        seed: Optional[int] = None,
    ) -> None:
        """
        Initialize the mock simulator.

        Args:
            failure_probabilities: Per-action-type failure probability override.
            action_durations: Per-action-type duration override (seconds).
            time_scale: Multiplier applied to all durations (0.5 = 2x faster).
            seed: Random seed for reproducibility.
        """
        self._failure_probs = failure_probabilities or dict(DEFAULT_FAILURE_PROBS)
        self._durations = action_durations or dict(DEFAULT_DURATIONS)
        self._time_scale = max(time_scale, 0.001)
        self._rng = random.Random(seed)

        self._arms: Dict[str, ArmState] = {}
        self._objects: Dict[str, ObjectState] = {}
        self._trace: List[TraceEntry] = []
        self._sim_time: float = 0.0
        self._is_running: bool = False
        self._initialized: bool = False
        self._scene_loaded: bool = False
        logger.info("MockSimulator created (time_scale=%.2f)", self._time_scale)

    # ------------------------------------------------------------------
    # SimulationInterface implementation
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        if self._initialized:
            logger.warning("MockSimulator already initialized")
            return
        self._initialized = True
        self._is_running = True
        logger.info("MockSimulator initialized")

    def load_scene(self, scene_config: dict) -> None:
        self._ensure_initialized()
        self._arms.clear()
        self._objects.clear()

        for arm_cfg in scene_config.get("robot_arms", []):
            pos_cfg = arm_cfg.get("position", {})
            arm = ArmState(
                arm_id=arm_cfg["id"],
                position=Position(**pos_cfg) if pos_cfg else Position(),
            )
            self._arms[arm.arm_id] = arm

        for obj_cfg in scene_config.get("objects", []):
            pos_cfg = obj_cfg.get("position", {})
            obj = ObjectState(
                object_id=obj_cfg["id"],
                object_type=obj_cfg.get("type", "unknown"),
                position=Position(**pos_cfg) if pos_cfg else Position(),
            )
            self._objects[obj.object_id] = obj

        self._scene_loaded = True
        logger.info(
            "Scene loaded: %d arms, %d objects",
            len(self._arms),
            len(self._objects),
        )

    def execute_action(self, arm_id: str, action: dict) -> ActionResult:
        self._ensure_running()
        action_type = action.get("type", "unknown")

        arm = self._arms.get(arm_id)
        if arm is None:
            result = ActionResult(
                success=False, duration=0.0,
                error_message=f"Unknown arm: {arm_id}",
            )
            self._record_trace(arm_id, action, result)
            return result

        if action_type not in self._durations:
            result = ActionResult(
                success=False, duration=0.0,
                error_message=f"Unknown action type: {action_type}",
            )
            self._record_trace(arm_id, action, result)
            return result

        # Simulate failure based on probability
        base_duration = self._durations[action_type] * self._time_scale
        fail_prob = self._failure_probs.get(action_type, 0.0)
        failed = self._rng.random() < fail_prob

        if failed:
            arm.status = ArmStatus.ERROR
            result = ActionResult(
                success=False,
                duration=base_duration,
                position=arm.position,
                error_message=f"Simulated {action_type} failure on {arm_id}",
                sensor_data={"simulated": True, "failure_reason": "random"},
            )
            self._sim_time += base_duration
            self._record_trace(arm_id, action, result)
            # Recover after failure
            arm.status = ArmStatus.IDLE
            return result

        # Successful execution -- update state
        result = self._execute_successful_action(arm, action, action_type, base_duration)
        self._sim_time += base_duration
        self._record_trace(arm_id, action, result)
        return result

    def get_state(self) -> SimulationState:
        return SimulationState(
            timestamp=self._sim_time,
            arm_states=dict(self._arms),
            object_states=dict(self._objects),
            is_running=self._is_running,
        )

    def step(self) -> None:
        self._ensure_running()
        self._sim_time += 0.1 * self._time_scale

    def reset(self) -> None:
        self._arms.clear()
        self._objects.clear()
        self._trace.clear()
        self._sim_time = 0.0
        self._is_running = False
        self._initialized = False
        self._scene_loaded = False
        logger.info("MockSimulator reset")

    def close(self) -> None:
        self._is_running = False
        logger.info(
            "MockSimulator closed (%d trace entries recorded)", len(self._trace)
        )

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    @property
    def execution_trace(self) -> List[TraceEntry]:
        """Return the full execution trace."""
        return list(self._trace)

    @property
    def sim_time(self) -> float:
        return self._sim_time

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            raise RuntimeError("MockSimulator has not been initialized; call initialize() first")

    def _ensure_running(self) -> None:
        self._ensure_initialized()
        if not self._is_running:
            raise RuntimeError("MockSimulator is not running")

    def _record_trace(self, arm_id: str, action: dict, result: ActionResult) -> None:
        self._trace.append(
            TraceEntry(
                timestamp=self._sim_time,
                arm_id=arm_id,
                action=action,
                result=result,
            )
        )

    def _execute_successful_action(
        self,
        arm: ArmState,
        action: dict,
        action_type: str,
        duration: float,
    ) -> ActionResult:
        sensor_data: Dict[str, Any] = {"simulated": True}

        if action_type == "move":
            target = action.get("position", {})
            if target:
                arm.position = Position(
                    x=target.get("x", arm.position.x),
                    y=target.get("y", arm.position.y),
                    z=target.get("z", arm.position.z),
                    roll=target.get("roll", arm.position.roll),
                    pitch=target.get("pitch", arm.position.pitch),
                    yaw=target.get("yaw", arm.position.yaw),
                )
            arm.status = ArmStatus.MOVING
            arm.status = ArmStatus.IDLE

        elif action_type == "pick":
            target_id = action.get("target")
            if target_id and target_id in self._objects:
                obj = self._objects[target_id]
                obj.status = ObjectStatus.GRASPED
                obj.held_by = arm.arm_id
                arm.held_object = target_id
                arm.gripper_open = False
                # Move arm to object position
                arm.position = Position(
                    x=obj.position.x, y=obj.position.y, z=obj.position.z
                )
                sensor_data["grasped_object"] = target_id
            arm.status = ArmStatus.EXECUTING
            arm.status = ArmStatus.IDLE

        elif action_type == "place":
            target = action.get("position", {})
            if arm.held_object and arm.held_object in self._objects:
                obj = self._objects[arm.held_object]
                obj.status = ObjectStatus.PLACED
                obj.held_by = None
                if target:
                    obj.position = Position(
                        x=target.get("x", obj.position.x),
                        y=target.get("y", obj.position.y),
                        z=target.get("z", obj.position.z),
                    )
                sensor_data["placed_object"] = arm.held_object
                arm.held_object = None
                arm.gripper_open = True
            arm.status = ArmStatus.EXECUTING
            arm.status = ArmStatus.IDLE

        elif action_type == "assemble":
            target_id = action.get("target")
            if target_id and target_id in self._objects:
                obj = self._objects[target_id]
                obj.status = ObjectStatus.DONE
                obj.properties["assembled"] = True
                sensor_data["assembled_object"] = target_id
            arm.status = ArmStatus.EXECUTING
            arm.status = ArmStatus.IDLE

        elif action_type == "inspect":
            target_id = action.get("target")
            if target_id and target_id in self._objects:
                obj = self._objects[target_id]
                sensor_data["inspected_object"] = target_id
                sensor_data["inspection_passed"] = self._rng.random() > 0.1
                sensor_data["quality_score"] = round(self._rng.uniform(0.7, 1.0), 3)
            arm.status = ArmStatus.EXECUTING
            arm.status = ArmStatus.IDLE

        return ActionResult(
            success=True,
            duration=duration,
            position=Position(
                x=arm.position.x, y=arm.position.y, z=arm.position.z
            ),
            sensor_data=sensor_data,
        )
