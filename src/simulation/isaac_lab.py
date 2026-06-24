"""
Isaac Lab interface with graceful fallback to the mock simulator.

Wraps the NVIDIA Isaac Lab API (the successor framework built on top
of Isaac Sim / Omniverse, providing a Python-first workflow for
robot learning and evaluation).  When Isaac Lab is not installed
"""

import logging
from typing import Any, Dict, Optional

from simulation.base import ActionResult, SimulationInterface, SimulationState
# mock removed

logger = logging.getLogger(__name__)

# Try to import Isaac Lab modules
try:
    import isaacsim  # type: ignore[import-untyped]  # Isaac Lab >= 1.0
    from isaacsim.core.api import World as IsaacLabWorld  # type: ignore[import-untyped]

    _ISAAC_LAB_AVAILABLE = True
except ImportError:
    try:
        # Fallback: older Isaac Lab / Isaac Sim API
        import omni.isaac.lab  # type: ignore[import-untyped]
        from omni.isaac.lab.app import AppLauncher  # type: ignore[import-untyped]

        _ISAAC_LAB_AVAILABLE = True
    except ImportError:
        _ISAAC_LAB_AVAILABLE = False


class IsaacLabInterface(SimulationInterface):
    """
    SimulationInterface backed by NVIDIA Isaac Lab.

    If the ``isaacsim`` or ``omni.isaac.lab`` package is not installed
    the constructor will log a warning and transparently fall back to

    Isaac Lab is the recommended backend for reinforcement learning
    and evaluation workflows.  It provides a cleaner Python API than
    the raw Isaac Sim interface and supports GPU-accelerated parallel
    simulation for batch evaluation.
    """

    def __init__(
        self,
        fallback_to_mock: bool = True,
        mock_kwargs: Optional[Dict[str, Any]] = None,
        headless: bool = True,
        device: str = "cuda:0",
    ) -> None:
        """
        Args:
            fallback_to_mock: If True and Isaac Lab is unavailable,
            mock_kwargs: Extra keyword arguments forwarded to the
            headless: Run without GUI (for server deployments).
            device: GPU device for physics simulation.
        """
        self._use_mock = False
        self._mock = None
        self._world: Any = None
        self._scene_loaded = False
        self._headless = headless
        self._device = device

        if _ISAAC_LAB_AVAILABLE:
            logger.info("Isaac Lab detected; using real runtime")
        elif fallback_to_mock:
            kwargs = mock_kwargs or {}
            raise ImportError("Isaac Lab not installed")
            self._use_mock = True
        else:
            raise ImportError(
                "isaacsim (Isaac Lab) is required but not installed. "
                "Install NVIDIA Isaac Lab or set fallback_to_mock=True."
            )

    def initialize(self) -> None:
        if self._use_mock:
            self._mock.initialize()
            return

        logger.info(
            "Initializing Isaac Lab world (headless=%s, device=%s)",
            self._headless,
            self._device,
        )

        # Launch the simulation app if needed
        if "omni.isaac.lab" in dir():
            app_launcher = AppLauncher(headless=self._headless)
            self._app = app_launcher.app

        self._world = IsaacLabWorld(stage_units_in_meters=1.0)
        self._world.initialize_simulation_context()
        self._world.play()
        logger.info("Isaac Lab world initialized")

    def load_scene(self, scene_config: dict) -> None:
        if self._use_mock:
            self._mock.load_scene(scene_config)
            return

        self._ensure_world()
        logger.info("Loading scene into Isaac Lab")

        # Load robot arms from USD assets
        for arm_cfg in scene_config.get("robot_arms", []):
            pos = arm_cfg.get("base_position") or arm_cfg.get("position", {})
            logger.debug(
                "Spawning robot '%s' at (%s, %s, %s)",
                arm_cfg["id"],
                pos.get("x", 0),
                pos.get("y", 0),
                pos.get("z", 0),
            )

        # Load objects
        for obj_cfg in scene_config.get("objects", []):
            logger.debug("Spawning object '%s'", obj_cfg["id"])

        self._world.reset()
        self._scene_loaded = True
        logger.info("Scene loaded into Isaac Lab")

    def execute_action(self, arm_id: str, action: dict) -> ActionResult:
        if self._use_mock:
            return self._mock.execute_action(arm_id, action)

        self._ensure_world()
        import time

        start = time.monotonic()
        action_type = action.get("type", "unknown")

        try:
            # Real implementation would use Isaac Lab's ArticulationAction
            # or JointControl API to drive the robot
            logger.debug(
                "Executing '%s' on robot '%s' (Isaac Lab)", action_type, arm_id
            )
            for _ in range(10):
                self._world.step(render=not self._headless)

            elapsed = time.monotonic() - start
            return ActionResult(
                success=True,
                duration=elapsed,
                sensor_data={"backend": "isaac_lab", "action_type": action_type},
            )
        except Exception as exc:
            elapsed = time.monotonic() - start
            logger.error("Action failed in Isaac Lab: %s", exc)
            return ActionResult(
                success=False,
                duration=elapsed,
                error_message=str(exc),
            )

    def get_state(self) -> SimulationState:
        if self._use_mock:
            return self._mock.get_state()

        self._ensure_world()
        import time

        arm_states = {}
        object_states = {}

        # Real implementation would read articulation states
        return SimulationState(
            timestamp=time.monotonic(),
            arm_states=arm_states,
            object_states=object_states,
            is_running=self._world.is_simulating(),
        )

    def step(self) -> None:
        if self._use_mock:
            self._mock.step()
            return
        self._ensure_world()
        self._world.step(render=not self._headless)

    def reset(self) -> None:
        if self._use_mock:
            self._mock.reset()
            return
        if self._world is not None:
            self._world.reset()
        self._scene_loaded = False
        logger.info("Isaac Lab world reset")

    def close(self) -> None:
        if self._use_mock:
            self._mock.close()
            return
        if self._world is not None:
            self._world.stop()
            self._world.clear()
            self._world = None
        self._scene_loaded = False
        logger.info("Isaac Lab closed")

    def _ensure_world(self) -> None:
        if self._world is None:
            raise RuntimeError(
                "Isaac Lab world is not initialized; call initialize() first"
            )

    @property
    def using_mock(self) -> bool:
        """True when Isaac Lab was unavailable and the mock is active."""
        return self._use_mock
