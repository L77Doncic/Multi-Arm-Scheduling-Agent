"""
Omniverse interface with graceful fallback to the mock simulator.

Wraps the NVIDIA Omniverse Kit API.  When Omniverse is not installed
the class silently delegates every call to :class:`MockSimulator`,
matching the pattern used by :class:`IsaacSimInterface`.
"""

import logging
from typing import Any, Dict, Optional

from simulation.base import ActionResult, SimulationInterface, SimulationState
from simulation.mock_simulator import MockSimulator

logger = logging.getLogger(__name__)

# Try to import Omniverse modules
try:
    import omni.kit  # type: ignore[import-untyped]
    import omni.usd  # type: ignore[import-untyped]

    _OMNIVERSE_AVAILABLE = True
except ImportError:
    _OMNIVERSE_AVAILABLE = False


class OmniverseInterface(SimulationInterface):
    """
    SimulationInterface backed by NVIDIA Omniverse Kit.

    If the ``omni.kit`` package is not installed the constructor will
    log a warning and transparently fall back to :class:`MockSimulator`.

    Omniverse differs from Isaac Sim in that it provides a general-purpose
    USD-based scene authoring and rendering framework, while Isaac Sim
    adds robot-specific physics and sensor simulation on top.  This
    interface allows the scheduling agent to work with either backend.
    """

    def __init__(
        self,
        fallback_to_mock: bool = True,
        mock_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._use_mock = False
        self._mock: Optional[MockSimulator] = None
        self._stage: Any = None
        self._scene_loaded = False

        if _OMNIVERSE_AVAILABLE:
            logger.info("Omniverse detected; using real runtime")
        elif fallback_to_mock:
            kwargs = mock_kwargs or {}
            self._mock = MockSimulator(**kwargs)
            self._use_mock = True
            logger.warning("Omniverse not installed -- falling back to MockSimulator")
        else:
            raise ImportError(
                "omni.kit is required but not installed. "
                "Install NVIDIA Omniverse or set fallback_to_mock=True."
            )

    def initialize(self) -> None:
        if self._use_mock:
            self._mock.initialize()
            return

        logger.info("Initializing Omniverse Kit")
        # In a real deployment, this would launch the Kit application
        # with the appropriate extensions loaded.
        self._stage = omni.usd.get_context().get_stage()
        logger.info("Omniverse stage acquired")

    def load_scene(self, scene_config: dict) -> None:
        if self._use_mock:
            self._mock.load_scene(scene_config)
            return

        logger.info("Loading scene into Omniverse")
        # Real implementation would spawn USD prims for robots and objects
        for arm_cfg in scene_config.get("robot_arms", []):
            logger.debug("Adding robot '%s' to Omniverse stage", arm_cfg["id"])

        for obj_cfg in scene_config.get("objects", []):
            logger.debug("Adding object '%s' to Omniverse stage", obj_cfg["id"])

        self._scene_loaded = True
        logger.info("Scene loaded into Omniverse")

    def execute_action(self, arm_id: str, action: dict) -> ActionResult:
        if self._use_mock:
            return self._mock.execute_action(arm_id, action)

        import time

        start = time.monotonic()
        action_type = action.get("type", "unknown")

        try:
            logger.debug(
                "Executing '%s' on robot '%s' (Omniverse)", action_type, arm_id
            )
            # Real implementation would drive the robot controller
            # through the Omniverse animation/physics framework
            elapsed = time.monotonic() - start
            return ActionResult(
                success=True,
                duration=elapsed,
                sensor_data={"backend": "omniverse", "action_type": action_type},
            )
        except Exception as exc:
            elapsed = time.monotonic() - start
            logger.error("Action failed in Omniverse: %s", exc)
            return ActionResult(
                success=False,
                duration=elapsed,
                error_message=str(exc),
            )

    def get_state(self) -> SimulationState:
        if self._use_mock:
            return self._mock.get_state()

        import time

        # Real implementation would read USD prims and return their poses
        return SimulationState(
            timestamp=time.monotonic(),
            arm_states={},
            object_states={},
            is_running=True,
        )

    def step(self) -> None:
        if self._use_mock:
            self._mock.step()
            return
        # Real implementation would advance the Omniverse simulation
        pass

    def reset(self) -> None:
        if self._use_mock:
            self._mock.reset()
            return
        self._scene_loaded = False
        logger.info("Omniverse stage reset")

    def close(self) -> None:
        if self._use_mock:
            self._mock.close()
            return
        self._stage = None
        self._scene_loaded = False
        logger.info("Omniverse closed")

    @property
    def using_mock(self) -> bool:
        """True when Omniverse was unavailable and the mock is active."""
        return self._use_mock
