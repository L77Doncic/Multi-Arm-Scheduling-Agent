"""
Arm Interface Adapter.

Bridges the atomic skill primitives used in generated code
(move_to, grip, release, etc.) to the simulation backend.
This allows LLM-generated or template-generated code to be
actually executed in the simulation environment.
"""

import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ArmInterface:
    """
    Adapter that exposes atomic primitives to generated task code.

    Each primitive call is translated into a simulation action and
    executed via the underlying :class:`SimulationInterface`.
    """

    def __init__(
        self,
        arm_id: str,
        simulation,
        estimated_duration: float = 3.0,
    ):
        """
        Args:
            arm_id: The robot arm ID in the simulation.
            simulation: A SimulationInterface instance.
            estimated_duration: Fallback duration if simulation
                doesn't provide one.
        """
        self.arm_id = arm_id
        self._sim = simulation
        self._estimated_duration = estimated_duration
        self._action_count = 0
        self._total_duration = 0.0
        self._errors: list = []
        self._sensor_data: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Atomic primitives — callable from generated code
    # ------------------------------------------------------------------

    def move_to(self, x: float, y: float, z: float, speed: float = 1.0) -> bool:
        """Move end-effector to absolute position."""
        return self._execute(
            "move",
            {
                "position": {"x": x, "y": y, "z": z},
                "speed": speed,
            },
        )

    def linear_move(self, dx: float, dy: float, dz: float, speed: float = 1.0) -> bool:
        """Move relative to current position."""
        # Get current position from simulation state
        try:
            state = self._sim.get_state()
            arm_state = state.arm_states.get(self.arm_id)
            if arm_state:
                new_x = arm_state.position.x + dx
                new_y = arm_state.position.y + dy
                new_z = arm_state.position.z + dz
                return self._execute(
                    "move",
                    {
                        "position": {"x": new_x, "y": new_y, "z": new_z},
                        "speed": speed,
                    },
                )
        except Exception:
            pass
        # Fallback: just execute a move action
        return self._execute("move", {"position": {"x": dx, "y": dy, "z": dz}})

    def grip(self, force: float = 50.0, target_id: str = "") -> bool:
        """Close gripper with specified force."""
        return self._execute("pick", {"force": force, "target": target_id})

    def release(self, target_id: str = "") -> bool:
        """Open gripper to release object at current position."""
        return self._execute("place", {"target": target_id, "position": {}})

    def rotate(
        self, roll: float = 0, pitch: float = 0, yaw: float = 0, speed: float = 1.0
    ) -> bool:
        """Rotate end-effector to orientation."""
        return self._execute(
            "move",
            {
                "position": {"roll": roll, "pitch": pitch, "yaw": yaw},
                "speed": speed,
            },
        )

    def wait(self, duration: float = 1.0) -> bool:
        """Wait for specified duration."""
        self._total_duration += duration
        return True

    def check_sensor(self, sensor_type: str) -> Dict[str, Any]:
        """Read sensor value (force, vision, proximity)."""
        self._action_count += 1

        # Try to get sensor data from simulation
        try:
            state = self._sim.get_state()
            arm_state = state.arm_states.get(self.arm_id)
            if arm_state and arm_state.held_object:
                obj_state = state.object_states.get(arm_state.held_object)
                if obj_state:
                    if sensor_type == "force":
                        return {"fz": 25.0, "tx": 0.0, "ty": 0.0, "tz": 0.0}
                    elif sensor_type == "vision":
                        return {"defect_score": 0.02, "alignment_ok": True}
        except Exception:
            pass

        # Return simulated sensor data
        defaults = {
            "force": {"fz": 30.0, "tx": 0.0, "ty": 0.0, "tz": 5.0},
            "vision": {"defect_score": 0.05, "alignment_ok": True, "quality": 0.95},
            "proximity": {"distance": 0.15, "detected": True},
            "weld_trigger": {"triggered": True},
        }
        result = defaults.get(sensor_type, {"value": 0.0})
        self._sensor_data[sensor_type] = result
        return result

    def set_payload(self, mass: float = 0.0) -> bool:
        """Declare current payload mass for dynamics."""
        self._action_count += 1
        return True

    def set_compliance(
        self,
        stiffness_x: float = 200,
        stiffness_y: float = 200,
        stiffness_z: float = 100,
    ) -> bool:
        """Set Cartesian stiffness for contact tasks."""
        self._action_count += 1
        return True

    # ------------------------------------------------------------------
    # Execution results
    # ------------------------------------------------------------------

    @property
    def total_duration(self) -> float:
        """Total simulated duration of all executed actions."""
        return self._total_duration

    @property
    def action_count(self) -> int:
        """Number of primitive calls made."""
        return self._action_count

    @property
    def errors(self) -> list:
        """List of errors encountered during execution."""
        return self._errors

    @property
    def success(self) -> bool:
        """True if no errors occurred."""
        return len(self._errors) == 0

    # ------------------------------------------------------------------
    # Internal helper
    # ------------------------------------------------------------------

    def _execute(self, action_type: str, params: Dict[str, Any]) -> bool:
        """Execute a simulation action and track results."""
        self._action_count += 1

        action = {"type": action_type, **params}
        if self._estimated_duration > 0:
            action["estimated_duration"] = self._estimated_duration / max(
                self._action_count, 1
            )

        try:
            result = self._sim.execute_action(self.arm_id, action)
            if result.duration > 0:
                self._total_duration += result.duration
            if not result.success:
                self._errors.append(result.error_message or f"{action_type} failed")
                logger.debug(
                    "ArmInterface %s: %s failed: %s",
                    self.arm_id,
                    action_type,
                    result.error_message,
                )
            return result.success
        except Exception as exc:
            self._errors.append(str(exc))
            logger.warning(
                "ArmInterface %s: %s exception: %s", self.arm_id, action_type, exc
            )
            return False


def execute_generated_code(
    code_str: str,
    arm_id: str,
    simulation,
    estimated_duration: float = 3.0,
) -> Dict[str, Any]:
    """
    Execute generated task code in the simulation.

    Args:
        code_str: Python source code containing an execute_* function.
        arm_id: The robot arm to control.
        simulation: The simulation interface.
        estimated_duration: Estimated task duration for time tracking.

    Returns:
        Dictionary with execution results (success, duration, errors, etc.)
    """
    import re

    # Create the arm interface
    interface = ArmInterface(arm_id, simulation, estimated_duration)

    # Execute the code in a namespace
    namespace: Dict[str, Any] = {"__name__": "__generated__"}
    namespace["time"] = time

    try:
        exec(code_str, namespace)
    except SyntaxError as exc:
        return {
            "success": False,
            "duration": 0.0,
            "error": f"Syntax error in generated code: {exc}",
            "action_count": 0,
        }
    except Exception as exc:
        return {
            "success": False,
            "duration": 0.0,
            "error": f"Error loading generated code: {exc}",
            "action_count": 0,
        }

    # Find the execute function
    func = None
    for name, obj in namespace.items():
        if callable(obj) and name.startswith("execute_"):
            func = obj
            break

    if func is None:
        return {
            "success": False,
            "duration": 0.0,
            "error": "No execute_* function found in generated code",
            "action_count": 0,
        }

    # Call the function with the arm interface
    try:
        result = func(interface)
        if not isinstance(result, dict):
            result = {"success": interface.success, "result": result}

        # Merge interface-level data
        result.setdefault("success", interface.success)
        result.setdefault("duration", interface.total_duration)
        result["action_count"] = interface.action_count
        if interface.errors:
            result["errors"] = interface.errors
            result["success"] = False

        return result

    except Exception as exc:
        logger.warning("Generated code execution failed: %s", exc)
        return {
            "success": False,
            "duration": interface.total_duration,
            "error": str(exc),
            "action_count": interface.action_count,
        }
