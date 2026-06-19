"""
Isaac Sim interface with graceful fallback to the mock simulator.

Wraps the NVIDIA Isaac Sim / Omniverse Kit API so that the rest of
the codebase can treat it as just another ``SimulationInterface``
implementation.  When Isaac Sim is not installed the class silently
delegates every call to :class:`MockSimulator`.
"""

import logging
from typing import Any, Dict, Optional

from simulation.base import (
    ActionResult,
    SimulationInterface,
    SimulationState,
)
from simulation.mock_simulator import MockSimulator

logger = logging.getLogger(__name__)

# Try to import Isaac Sim modules; these are only available inside
# the Omniverse runtime.
try:
    import omni.isaac.core  # type: ignore[import-untyped]
    from omni.isaac.core import World as IsaacWorld  # type: ignore[import-untyped]
    _ISAAC_AVAILABLE = True
except ImportError:
    _ISAAC_AVAILABLE = False


class IsaacSimInterface(SimulationInterface):
    """
    SimulationInterface backed by NVIDIA Isaac Sim.

    If the ``omni.isaac.core`` package is not installed the
    constructor will log a warning and transparently fall back to
    :class:`MockSimulator` so that tests and development can proceed
    without the full Omniverse stack.
    """

    def __init__(
        self,
        fallback_to_mock: bool = True,
        mock_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Args:
            fallback_to_mock: If True and Isaac Sim is unavailable,
                silently delegate to MockSimulator.
            mock_kwargs: Extra keyword arguments forwarded to the
                MockSimulator constructor when falling back.
        """
        self._world: Any = None  # IsaacWorld or None
        self._use_mock = False
        self._mock: Optional[MockSimulator] = None
        self._scene_loaded = False

        if _ISAAC_AVAILABLE:
            logger.info("Isaac Sim detected; using real runtime")
        elif fallback_to_mock:
            kwargs = mock_kwargs or {}
            self._mock = MockSimulator(**kwargs)
            self._use_mock = True
            logger.warning(
                "Isaac Sim not installed -- falling back to MockSimulator"
            )
        else:
            raise ImportError(
                "omni.isaac.core is required but not installed. "
                "Install NVIDIA Isaac Sim or set fallback_to_mock=True."
            )

    # ------------------------------------------------------------------
    # SimulationInterface
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        if self._use_mock:
            self._mock.initialize()  # type: ignore[union-attr]
            return

        logger.info("Initializing Isaac Sim world")
        self._world = IsaacWorld(stage_units_in_meters=1.0)
        self._world.initialize_simulation_context()
        self._world.play()
        logger.info("Isaac Sim world initialized")

    def load_scene(self, scene_config: dict) -> None:
        if self._use_mock:
            self._mock.load_scene(scene_config)  # type: ignore[union-attr]
            return

        self._ensure_world()
        logger.info("Loading scene into Isaac Sim")

        from omni.isaac.core.objects import DynamicCuboid  # type: ignore[import-untyped]
        from omni.isaac.core.robots import Robot  # type: ignore[import-untyped]

        # Load robot arms
        for arm_cfg in scene_config.get("robot_arms", []):
            pos = arm_cfg.get("position", {})
            logger.debug(
                "Adding robot '%s' at (%s, %s, %s)",
                arm_cfg["id"],
                pos.get("x", 0), pos.get("y", 0), pos.get("z", 0),
            )
            # Real implementation would call omni.isaac.core to spawn
            # the robot USD asset.  We log the intent for now.
            self._world.scene.add(
                Robot(
                    prim_path=f"/World/Robots/{arm_cfg['id']}",
                    name=arm_cfg["id"],
                    position=[pos.get("x", 0), pos.get("y", 0), pos.get("z", 0)],
                )
            )

        # Load objects
        for obj_cfg in scene_config.get("objects", []):
            pos = obj_cfg.get("position", {})
            scale = obj_cfg.get("scale", [0.05, 0.05, 0.05])
            self._world.scene.add(
                DynamicCuboid(
                    prim_path=f"/World/Objects/{obj_cfg['id']}",
                    name=obj_cfg["id"],
                    position=[pos.get("x", 0), pos.get("y", 0), pos.get("z", 0)],
                    scale=scale,
                )
            )

        self._world.reset()
        self._scene_loaded = True
        logger.info("Scene loaded into Isaac Sim")

    def execute_action(self, arm_id: str, action: dict) -> ActionResult:
        if self._use_mock:
            return self._mock.execute_action(arm_id, action)  # type: ignore[union-attr]

        self._ensure_world()
        import time

        action_type = action.get("type", "unknown")
        start = time.monotonic()

        try:
            robot = self._world.scene.get_object(arm_id)
            if robot is None:
                return ActionResult(
                    success=False,
                    duration=0.0,
                    error_message=f"Robot '{arm_id}' not found in scene",
                )

            # Dispatch based on action type
            if action_type == "move":
                target = action.get("position", {})
                robot.set_world_pose(
                    position=[
                        target.get("x", 0),
                        target.get("y", 0),
                        target.get("z", 0),
                    ]
                )
            elif action_type in ("pick", "place", "assemble", "inspect"):
                # In a real integration these would drive the arm controller.
                logger.debug(
                    "Executing '%s' on robot '%s' (Isaac Sim)", action_type, arm_id
                )
                # Step the physics world a few times to let the action play out
                for _ in range(10):
                    self._world.step(render=False)

            elapsed = time.monotonic() - start
            return ActionResult(
                success=True,
                duration=elapsed,
                sensor_data={"backend": "isaac_sim", "action_type": action_type},
            )

        except Exception as exc:
            elapsed = time.monotonic() - start
            logger.error("Action failed in Isaac Sim: %s", exc, exc_info=True)
            return ActionResult(
                success=False,
                duration=elapsed,
                error_message=str(exc),
            )

    def get_state(self) -> SimulationState:
        if self._use_mock:
            return self._mock.get_state()  # type: ignore[union-attr]

        self._ensure_world()
        import time

        arm_states = {}
        object_states = {}
        is_running = self._world.is_simulating()

        for obj in self._world.scene.objects:
            name = obj.name
            pose, _ = obj.get_world_pose()
            if name.startswith("arm_"):
                from simulation.base import ArmState, Position
                arm_states[name] = ArmState(
                    arm_id=name,
                    position=Position(x=pose[0], y=pose[1], z=pose[2]),
                )
            else:
                from simulation.base import ObjectState, Position
                object_states[name] = ObjectState(
                    object_id=name,
                    object_type="unknown",
                    position=Position(x=pose[0], y=pose[1], z=pose[2]),
                )

        return SimulationState(
            timestamp=time.monotonic(),
            arm_states=arm_states,
            object_states=object_states,
            is_running=is_running,
        )

    def step(self) -> None:
        if self._use_mock:
            self._mock.step()  # type: ignore[union-attr]
            return
        self._ensure_world()
        self._world.step(render=False)

    def reset(self) -> None:
        if self._use_mock:
            self._mock.reset()  # type: ignore[union-attr]
            return
        if self._world is not None:
            self._world.reset()
        self._scene_loaded = False
        logger.info("Isaac Sim world reset")

    def close(self) -> None:
        if self._use_mock:
            self._mock.close()  # type: ignore[union-attr]
            return
        if self._world is not None:
            self._world.stop()
            self._world.clear()
            self._world = None
        self._scene_loaded = False
        logger.info("Isaac Sim world closed")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _ensure_world(self) -> None:
        if self._world is None:
            raise RuntimeError(
                "Isaac Sim world is not initialized; call initialize() first"
            )

    @property
    def using_mock(self) -> bool:
        """True when Isaac Sim was unavailable and the mock is active."""
        return self._use_mock
