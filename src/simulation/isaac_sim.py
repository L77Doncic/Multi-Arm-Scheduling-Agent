"""
Isaac Sim interface with graceful fallback to the mock simulator.

Wraps the NVIDIA Isaac Sim / Omniverse Kit API so that the rest of
the codebase can treat it as just another ``SimulationInterface``
implementation.  When Isaac Sim is not installed the class silently
delegates every call to :class:`MockSimulator`.

NOTE: The Isaac Sim pip package requires creating a SimulationApp
BEFORE importing omni.isaac.core.  This module handles that ordering
automatically via lazy initialization in the initialize() method.
"""

import logging
import os
from typing import Any, Dict, Optional

from simulation.base import (
    ActionResult,
    SimulationInterface,
    SimulationState,
)
from simulation.mock_simulator import MockSimulator

logger = logging.getLogger(__name__)

# Check if the isaacsim pip package is installed (without importing
# omni.isaac.core which requires SimulationApp to be running).
_ISAACSIM_PACKAGE = False
try:
    import isaacsim  # noqa: F401
    _ISAACSIM_PACKAGE = True
except ImportError:
    pass


class IsaacSimInterface(SimulationInterface):
    """
    SimulationInterface backed by NVIDIA Isaac Sim.

    If the ``isaacsim`` package is not installed the constructor will
    log a warning and transparently fall back to :class:`MockSimulator`
    so that tests and development can proceed without the full
    Omniverse stack.

    Usage::

        sim = IsaacSimInterface(fallback_to_mock=True)
        sim.initialize()          # Creates SimulationApp + World
        sim.load_scene(scene)
        result = sim.execute_action("arm_001", {"type": "move", ...})
        sim.close()
    """

    def __init__(
        self,
        fallback_to_mock: bool = True,
        mock_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._app: Any = None  # SimulationApp
        self._world: Any = None  # IsaacWorld or None
        self._use_mock = False
        self._mock: Optional[MockSimulator] = None
        self._scene_loaded = False
        self._initialized = False

        if _ISAACSIM_PACKAGE:
            logger.info("isaacsim package detected; will initialize on initialize()")
        elif fallback_to_mock:
            kwargs = mock_kwargs or {}
            self._mock = MockSimulator(**kwargs)
            self._use_mock = True
            logger.warning(
                "isaacsim package not installed -- falling back to MockSimulator"
            )
        else:
            raise ImportError(
                "isaacsim package is required but not installed. "
                "Install with: pip install isaacsim --extra-index-url https://pypi.nvidia.com"
            )

    # ------------------------------------------------------------------
    # SimulationInterface
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        if self._use_mock:
            self._mock.initialize()  # type: ignore[union-attr]
            return

        if self._initialized:
            return

        logger.info("Initializing Isaac Sim SimulationApp...")

        # Set environment variables for headless operation
        os.environ.setdefault("ACCEPT_EULA", "Y")
        os.environ.setdefault(
            "VK_ICD_FILENAMES",
            "/tmp/vulkan_icd/nvidia_icd.json",
        )

        # Ensure LD_LIBRARY_PATH includes the USD libs directory
        usd_libs = None
        import pathlib
        ov_data = pathlib.Path.home() / ".local/share/ov/data/exts/v2"
        for d in ov_data.iterdir():
            if d.name.startswith("omni.usd.libs"):
                usd_libs = str(d / "bin")
                break
        if usd_libs:
            ld_path = os.environ.get("LD_LIBRARY_PATH", "")
            if usd_libs not in ld_path:
                os.environ["LD_LIBRARY_PATH"] = f"{usd_libs}:{ld_path}"

        # Create SimulationApp (bootstraps the Omniverse runtime)
        from isaacsim import SimulationApp  # type: ignore[import-untyped]

        self._app = SimulationApp({
            "headless": True,
            "exclude_ext_patterns": [
                "omni.physx.demos*",
                "omni.physx.vehicle*",
                "isaacsim.asset.importer.urdf*",
            ],
        })
        logger.info("SimulationApp created")

        # NOW we can import omni.isaac.core
        from omni.isaac.core import World as IsaacWorld  # type: ignore[import-untyped]

        self._IsaacWorld = IsaacWorld
        self._initialized = True
        logger.info("Isaac Sim initialized successfully")

    def load_scene(self, scene_config: dict) -> None:
        if self._use_mock:
            self._mock.load_scene(scene_config)  # type: ignore[union-attr]
            return

        self._ensure_initialized()
        logger.info("Loading scene into Isaac Sim")

        self._world = self._IsaacWorld(stage_units_in_meters=1.0)
        # Isaac Sim 4.5+ changed the initialization API
        if hasattr(self._world, 'initialize_simulation_context'):
            self._world.initialize_simulation_context()
        elif hasattr(self._world, 'initialize_physics'):
            self._world.initialize_physics()

        from omni.isaac.core.objects import DynamicCuboid  # type: ignore[import-untyped]
        from pxr import UsdGeom, Usd  # type: ignore[import-untyped]
        import omni.usd  # type: ignore[import-untyped]

        stage = omni.usd.get_context().get_stage()

        # Create root Xform for the scene
        UsdGeom.Xform.Define(stage, "/World")
        UsdGeom.Xform.Define(stage, "/World/Robots")
        UsdGeom.Xform.Define(stage, "/World/Objects")

        # Load robot arms as Xform prims (no USD robot asset available)
        for arm_cfg in scene_config.get("robot_arms", []):
            pos = arm_cfg.get("position", {})
            prim_path = f"/World/Robots/{arm_cfg['id']}"
            logger.debug(
                "Adding robot '%s' at (%s, %s, %s)",
                arm_cfg["id"],
                pos.get("x", 0), pos.get("y", 0), pos.get("z", 0),
            )
            xform = UsdGeom.Xform.Define(stage, prim_path)
            xform.AddTranslateOp().Set((
                pos.get("x", 0), pos.get("y", 0), pos.get("z", 0)
            ))

        # Load objects as dynamic cuboids
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

        self._ensure_initialized()
        import time

        action_type = action.get("type", "unknown")
        start = time.monotonic()

        try:
            # Try to get from scene first, fall back to USD prim
            robot = self._world.scene.get_object(arm_id)
            if robot is None:
                # Check if the prim exists in USD
                from pxr import UsdGeom  # type: ignore[import-untyped]
                import omni.usd  # type: ignore[import-untyped]
                stage = omni.usd.get_context().get_stage()
                prim = stage.GetPrimAtPath(f"/World/Robots/{arm_id}")
                if not prim.IsValid():
                    return ActionResult(
                        success=False,
                        duration=0.0,
                        error_message=f"Robot '{arm_id}' not found in scene",
                    )

            # Dispatch based on action type
            if action_type == "move":
                target = action.get("position", {})
                # Try Robot API first, fall back to Xform
                if robot is not None and hasattr(robot, 'set_world_pose'):
                    robot.set_world_pose(
                        position=[
                            target.get("x", 0),
                            target.get("y", 0),
                            target.get("z", 0),
                        ]
                    )
                else:
                    from pxr import UsdGeom  # type: ignore[import-untyped]
                    import omni.usd  # type: ignore[import-untyped]
                    stage = omni.usd.get_context().get_stage()
                    prim = stage.GetPrimAtPath(f"/World/Robots/{arm_id}")
                    if prim.IsValid():
                        xform = UsdGeom.Xform(prim)
                        # Use existing translate op or create new one
                        translate_ops = [
                            op for op in xform.GetOrderedXformOps()
                            if op.GetOpType() == UsdGeom.XformOp.TypeTranslate
                        ]
                        if translate_ops:
                            translate_ops[0].Set((
                                target.get("x", 0),
                                target.get("y", 0),
                                target.get("z", 0),
                            ))
                        else:
                            xform.AddTranslateOp().Set((
                                target.get("x", 0),
                                target.get("y", 0),
                                target.get("z", 0),
                            ))
            elif action_type in ("pick", "place", "assemble", "inspect"):
                logger.debug(
                    "Executing '%s' on robot '%s' (Isaac Sim)", action_type, arm_id
                )
                # Step the physics world to let the action play out
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

        self._ensure_initialized()
        import time

        arm_states = {}
        object_states = {}
        is_running = self._world.is_simulating()

        # Get states from scene objects
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

        # Also get robot states from USD prims
        try:
            from pxr import UsdGeom  # type: ignore[import-untyped]
            import omni.usd  # type: ignore[import-untyped]
            stage = omni.usd.get_context().get_stage()
            robots_prim = stage.GetPrimAtPath("/World/Robots")
            if robots_prim.IsValid():
                for child in robots_prim.GetChildren():
                    name = child.GetName()
                    if name not in arm_states:
                        xform = UsdGeom.Xform(child)
                        if xform:
                            from simulation.base import ArmState, Position
                            # Get translation from the Xform
                            translate_ops = xform.GetTranslateOp()
                            if translate_ops:
                                pos = translate_ops.Get()
                                arm_states[name] = ArmState(
                                    arm_id=name,
                                    position=Position(x=pos[0], y=pos[1], z=pos[2]),
                                )
        except Exception:
            pass  # USD queries are best-effort

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
        self._ensure_initialized()
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
        if self._app is not None:
            self._app.close()
            self._app = None
        self._scene_loaded = False
        self._initialized = False
        logger.info("Isaac Sim world closed")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            raise RuntimeError(
                "Isaac Sim is not initialized; call initialize() first"
            )

    @property
    def using_mock(self) -> bool:
        """True when Isaac Sim was unavailable and the mock is active."""
        return self._use_mock
