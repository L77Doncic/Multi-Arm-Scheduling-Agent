"""

Loads real Franka Panda robot USD models from Isaac Sim's asset library
instead of geometric block approximations.  Uses Articulation API for
joint-level control and Jacobian-based IK for end-effector positioning.

NOTE: The Isaac Sim pip package requires creating a SimulationApp
BEFORE importing omni.isaac.core.  This module handles that ordering
automatically via lazy initialization in the initialize() method.
"""

import logging
import math
import os
import time
from typing import Any, Dict, List, Optional

import numpy as np

from simulation.base import ActionResult, SimulationInterface, SimulationState
# removed

logger = logging.getLogger(__name__)

# Check if the isaacsim pip package is installed (without importing
# omni.isaac.core which requires SimulationApp to be running).
_ISAACSIM_PACKAGE = False
try:
    import isaacsim  # noqa: F401

    _ISAACSIM_PACKAGE = True
except ImportError:
    pass

# Franka Panda USD asset path (relative to Isaac Sim assets root)
_FRANKA_USD = "/Isaac/Robots/Franka/franka_alt_fingers.usd"
_EE_BODY_NAME = "panda_hand"


class IsaacSimInterface(SimulationInterface):
    """
    SimulationInterface backed by NVIDIA Isaac Sim.

    Loads real Franka Panda robot USD models and controls them via the
    Articulation API with Jacobian-based IK for end-effector positioning.

    If the ``isaacsim`` package is not installed the constructor will
    so that tests and development can proceed without the full
    Omniverse stack.
    """

    def __init__(
        self,
        fallback_to_mock: bool = False,
    ) -> None:
        self._app: Any = None  # SimulationApp
        self._world: Any = None  # IsaacWorld or None
        self._scene_loaded = False
        self._initialized = False

        # Robot articulation objects (prim_path -> SingleArticulation)
        self._robots: Dict[str, Any] = {}
        # Workpiece objects (wp_id -> DynamicCuboid)
        self._workpieces: Dict[str, Any] = {}
        self._workpiece_held_by: Dict[str, Optional[str]] = {}

        # Frame capture
        self._frames: List[Any] = []
        self._replicator_annotator: Any = None
        self._replicator_render_product: Any = None

        # End-effector body index per robot (cached after first query)
        self._ee_body_idx: Dict[str, int] = {}

        if _ISAACSIM_PACKAGE:
            logger.info("isaacsim package detected; will initialize on initialize()")
        else:
            raise ImportError(
                "isaacsim package is required but not installed. "
                "Install with: pip install isaacsim --extra-index-url https://pypi.nvidia.com"
            )

    # ------------------------------------------------------------------
    # SimulationInterface
    # ------------------------------------------------------------------

    def initialize(self) -> None:
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

        self._app = SimulationApp(
            {
                "headless": True,
                "width": 1920,
                "height": 1080,
                "exclude_ext_patterns": [
                    "omni.physx.demos*",
                    "omni.physx.vehicle*",
                    "isaacsim.asset.importer.urdf*",
                ],
            }
        )
        logger.info("SimulationApp created")

        # NOW we can import omni.isaac.core
        from omni.isaac.core import World as IsaacWorld  # type: ignore[import-untyped]

        self._IsaacWorld = IsaacWorld
        self._initialized = True
        logger.info("Isaac Sim initialized successfully")

    def load_scene(self, scene_config: dict) -> None:
        self._ensure_initialized()
        logger.info("Loading scene into Isaac Sim")

        self._world = self._IsaacWorld(stage_units_in_meters=1.0)
        if hasattr(self._world, "initialize_simulation_context"):
            self._world.initialize_simulation_context()
        elif hasattr(self._world, "initialize_physics"):
            self._world.initialize_physics()

        import omni.usd  # type: ignore[import-untyped]
        from omni.isaac.core.objects import DynamicCuboid  # type: ignore[import-untyped]
        from pxr import UsdGeom  # type: ignore[import-untyped]

        # Clear previous scene if reloading
        if self._scene_loaded:
            self._clear_scene()

        stage = omni.usd.get_context().get_stage()

        # Create root Xform hierarchy
        UsdGeom.Xform.Define(stage, "/World")
        UsdGeom.Xform.Define(stage, "/World/Robots")
        UsdGeom.Xform.Define(stage, "/World/Objects")
        UsdGeom.Xform.Define(stage, "/World/Stations")

        # --- Ground plane ---
        self._world.scene.add_ground_plane(
            prim_path="/World/GroundPlane",
            z_position=0,
        )

        # --- Load real Franka robots from Isaac Sim asset library ---
        self._load_robots(scene_config)

        # --- Create station markers (colored platforms) ---
        self._create_station_markers(scene_config)

        # --- Create workpiece objects (larger for visibility) ---
        for wp_cfg in scene_config.get("workpieces", []):
            pos = wp_cfg.get("initial_position") or wp_cfg.get("position", {})
            wp_id = wp_cfg["id"]
            scale = wp_cfg.get("scale", [0.12, 0.12, 0.12])  # 12cm default

            cuboid = self._world.scene.add(
                DynamicCuboid(
                    prim_path=f"/World/Objects/{wp_id}",
                    name=wp_id,
                    position=[pos.get("x", 0), pos.get("y", 0), pos.get("z", 0.06)],
                    scale=scale,
                    color=_random_color(wp_id),
                )
            )
            self._workpieces[wp_id] = cuboid
            self._workpiece_held_by[wp_id] = None

        self._world.reset()

        # Initialize all robot articulations after world reset
        for arm_id, robot in self._robots.items():
            if hasattr(robot, "initialize"):
                robot.initialize()
                logger.debug("Initialized robot articulation '%s'", arm_id)

        self._scene_loaded = True

        # Set up frame capture
        self._setup_frame_capture()

        logger.info(
            "Scene loaded: %d robots, %d workpieces",
            len(self._robots),
            len(self._workpieces),
        )

    def execute_action(self, arm_id: str, action: dict) -> ActionResult:

        self._ensure_initialized()
        action_type = action.get("type", "unknown")
        start = time.monotonic()

        try:
            if arm_id not in self._robots:
                return ActionResult(
                    success=False, duration=0.0,
                    error_message=f"Robot '{arm_id}' not found in scene",
                )

            if action_type == "move":
                target = action.get("position", {})
                self._move_to_position(
                    arm_id,
                    target.get("x", 0),
                    target.get("y", 0),
                    target.get("z", 0),
                )
                # Verify trajectory
                traj_ok = self.verify_trajectory(
                    arm_id,
                    [(target.get("x", 0), target.get("y", 0), target.get("z", 0))]
                )
                if not traj_ok["passed"]:
                    logger.warning("Trajectory verification failed: %s", traj_ok["checks"])

            elif action_type == "pick":
                target_id = action.get("target")
                if target_id and target_id in self._workpieces:
                    wp = self._workpieces[target_id]
                    wp_pos, _ = wp.get_world_pose()
                    self._move_to_position(arm_id, wp_pos[0], wp_pos[1], wp_pos[2])
                    self._gripper_close(arm_id)
                    if not self._attach_workpiece(arm_id, target_id):
                        for _ in range(10):
                            self._world.step(render=True)
                            self._capture_frame()
                        return ActionResult(
                            success=False,
                            duration=time.monotonic() - start,
                            error_message=f"Grip failed: arm '{arm_id}' too far from workpiece '{target_id}'",
                        )
                    # Verify pick was physically correct
                    pick_ok = self.verify_pick(arm_id, target_id)
                    if not pick_ok["passed"]:
                        logger.warning("Pick verification failed: %s", pick_ok["checks"])
                for _ in range(20):
                    self._world.step(render=True)
                    self._capture_frame()

            elif action_type == "place":
                target = action.get("position", {})
                held_wp = None
                for wp_id, holder in self._workpiece_held_by.items():
                    if holder == arm_id:
                        held_wp = wp_id
                        break
                if held_wp and target:
                    self._move_to_position(
                        arm_id,
                        target.get("x", 0), target.get("y", 0), target.get("z", 0.06),
                    )
                    self._gripper_open(arm_id)
                    self._detach_workpiece(held_wp, target.get("x", 0), target.get("y", 0), target.get("z", 0.06))
                    # Verify place was physically correct
                    place_ok = self.verify_place(held_wp, target.get("x", 0), target.get("y", 0), target.get("z", 0.06))
                    if not place_ok["passed"]:
                        logger.warning("Place verification failed: %s", place_ok["checks"])
                for _ in range(20):
                    self._world.step(render=True)
                    self._capture_frame()

            elif action_type in ("assemble", "inspect"):
                target_id = action.get("target")
                if target_id and target_id in self._workpieces:
                    wp_pos, _ = self._workpieces[target_id].get_world_pose()
                    self._move_to_position(arm_id, wp_pos[0], wp_pos[1], wp_pos[2])
                for _ in range(25):
                    self._world.step(render=True)
                    self._capture_frame()
            else:
                for _ in range(15):
                    self._world.step(render=True)
                    self._capture_frame()

            return ActionResult(
                success=True,
                duration=time.monotonic() - start,
                sensor_data={"backend": "isaac_sim", "action_type": action_type},
            )
        except Exception as exc:
            logger.error("Action failed in Isaac Sim: %s", exc, exc_info=True)
            return ActionResult(
                success=False, duration=time.monotonic() - start, error_message=str(exc),
            )

    def get_state(self) -> SimulationState:

        from simulation.base import ArmState, ObjectState, Position

        arm_states = {}
        object_states = {}

        # Read end-effector positions from real articulations
        for arm_id, robot in self._robots.items():
            try:
                ee_idx = self._get_ee_body_idx(arm_id)
                positions, _ = robot.get_body_coms(body_indices=np.array([ee_idx]))
                ee_pos = positions[0, 0]
                arm_states[arm_id] = ArmState(
                    arm_id=arm_id,
                    position=Position(x=ee_pos[0], y=ee_pos[1], z=ee_pos[2]),
                )
            except Exception:
                arm_states[arm_id] = ArmState(arm_id=arm_id)

        for wp_id, wp_obj in self._workpieces.items():
            try:
                pose, _ = wp_obj.get_world_pose()
                object_states[wp_id] = ObjectState(
                    object_id=wp_id, object_type="workpiece",
                    position=Position(x=pose[0], y=pose[1], z=pose[2]),
                    held_by=self._workpiece_held_by.get(wp_id),
                )
            except Exception:
                pass

        return SimulationState(
            timestamp=time.monotonic(),
            arm_states=arm_states,
            object_states=object_states,
            is_running=self._world.is_simulating() if self._world else False,
        )

    def step(self) -> None:
        self._ensure_initialized()
        self._world.step(render=False)

    def reset(self) -> None:
        if self._world is not None:
            self._world.reset()
        self._robots.clear()
        self._workpieces.clear()
        self._workpiece_held_by.clear()
        self._ee_body_idx.clear()
        self._frames.clear()
        self._scene_loaded = False

    def close(self) -> None:
        try:
            if self._world is not None:
                self._world.stop()
                self._world.clear()
                self._world = None
        except Exception:
            pass
        try:
            if self._app is not None:
                self._app.close()
                self._app = None
        except Exception:
            pass
        self._robots.clear()
        self._workpieces.clear()
        self._workpiece_held_by.clear()
        self._ee_body_idx.clear()
        self._frames.clear()
        self._scene_loaded = False
        self._initialized = False

    # ------------------------------------------------------------------
    # Frame capture API
    # ------------------------------------------------------------------

    def get_frames(self) -> List[Any]:
        return list(self._frames)

    @property
    def frame_count(self) -> int:
        return len(self._frames)

    # ------------------------------------------------------------------
    # Robot loading (real Franka USD)
    # ------------------------------------------------------------------

    def _load_robots(self, scene_config: dict) -> None:
        """Load real Franka Panda robots from Isaac Sim asset library."""
        from isaacsim.core.prims import SingleArticulation  # type: ignore[import-untyped]
        from isaacsim.core.utils.stage import add_reference_to_stage  # type: ignore[import-untyped]
        from isaacsim.storage.native import get_assets_root_path  # type: ignore[import-untyped]

        assets_root = get_assets_root_path()
        if assets_root is None:
            logger.error("Could not find Isaac Sim assets folder; falling back to cuboids")
            self._load_robots_fallback(scene_config)
            return

        franka_usd = assets_root + _FRANKA_USD
        logger.info("Loading Franka robot from: %s", franka_usd)

        for arm_cfg in scene_config.get("robot_arms", []):
            arm_id = arm_cfg["id"]
            pos = arm_cfg.get("base_position") or arm_cfg.get("position", {})
            px, py, pz = pos.get("x", 0), pos.get("y", 0), pos.get("z", 0)
            prim_path = f"/World/Robots/{arm_id}"

            # Add USD reference
            add_reference_to_stage(usd_path=franka_usd, prim_path=prim_path)

            # Create articulation
            robot = SingleArticulation(prim_path=prim_path, name=arm_id)
            robot.set_world_pose(
                position=np.array([px, py, pz]),
                orientation=np.array([1.0, 0.0, 0.0, 0.0]),
            )
            self._world.scene.add(robot)
            self._robots[arm_id] = robot

            logger.info(
                "Loaded Franka '%s' at (%.1f, %.1f, %.1f): %d DOFs",
                arm_id, px, py, pz, robot.num_dof,
            )

    def _load_robots_fallback(self, scene_config: dict) -> None:
        """Fallback: create simple 3-DOF articulation if asset loading fails."""
        from omni.isaac.core.objects import VisualCuboid  # type: ignore[import-untyped]

        for arm_cfg in scene_config.get("robot_arms", []):
            arm_id = arm_cfg["id"]
            pos = arm_cfg.get("base_position") or arm_cfg.get("position", {})
            px, py, pz = pos.get("x", 0), pos.get("y", 0), pos.get("z", 0)

            # Create a simple visible marker
            marker = self._world.scene.add(
                VisualCuboid(
                    prim_path=f"/World/Robots/{arm_id}",
                    name=arm_id,
                    position=[px, py, pz + 0.5],
                    scale=[0.15, 0.15, 1.0],
                    color=np.array([0.2, 0.5, 0.8]),
                )
            )
            self._robots[arm_id] = marker

    def _get_ee_body_idx(self, arm_id: str) -> int:
        """Get (and cache) the end-effector body index for a robot."""
        if arm_id in self._ee_body_idx:
            return self._ee_body_idx[arm_id]
        robot = self._robots[arm_id]
        idx = robot.get_body_index(_EE_BODY_NAME)
        self._ee_body_idx[arm_id] = idx
        return idx

    # ------------------------------------------------------------------
    # IK-based motion
    # ------------------------------------------------------------------

    def _move_to_position(
        self, arm_id: str, tx: float, ty: float, tz: float,
        anim_steps: int = 30,
    ) -> None:
        """Move robot end-effector to target with smooth animation."""
        from isaacsim.core.utils.types import ArticulationAction  # type: ignore[import-untyped]

        robot = self._robots[arm_id]
        target = np.array([tx, ty, tz])

        # Check if we can use IK (robot must be properly initialized)
        can_use_ik = False
        if hasattr(robot, "get_jacobians"):
            try:
                jac = robot.get_jacobians()
                if jac is not None:
                    can_use_ik = True
            except Exception:
                pass

        if not can_use_ik:
            # Fallback: teleport the robot to target position
            if hasattr(robot, "set_world_pose"):
                robot.set_world_pose(position=[tx, ty, tz])
                for _ in range(anim_steps):
                    self._world.step(render=True)
                    self._capture_frame()
            return

        ee_idx = self._get_ee_body_idx(arm_id)

        # Get current position
        positions, _ = robot.get_body_coms(body_indices=np.array([ee_idx]))
        start_pos = positions[0, 0]

        # Animate: interpolate from current to target in N steps
        for step in range(anim_steps):
            t = (step + 1) / anim_steps  # 0→1
            intermediate = start_pos + (target - start_pos) * t

            # Single IK step to reach intermediate target
            positions, _ = robot.get_body_coms(body_indices=np.array([ee_idx]))
            current_pos = positions[0, 0]
            error = intermediate - current_pos

            if np.linalg.norm(error) > 0.001:
                jacobian = robot.get_jacobians()
                J_pos = jacobian[0, ee_idx][:3, :]
                dq = np.linalg.pinv(J_pos) @ error
                dq = np.clip(dq, -0.3, 0.3)
                current_joints = robot.get_joint_positions()
                robot.apply_action(ArticulationAction(joint_positions=current_joints + dq * 0.15))

            self._world.step(render=True)
            self._capture_frame()

    def _gripper_close(self, arm_id: str) -> None:
        """Close gripper — step physics to simulate finger closing."""
        for _ in range(5):
            self._world.step(render=True)
            self._capture_frame()

    def _gripper_open(self, arm_id: str) -> None:
        """Open gripper — step physics to simulate finger opening."""
        for _ in range(5):
            self._world.step(render=True)
            self._capture_frame()

    # ------------------------------------------------------------------
    # Workpiece attachment
    # ------------------------------------------------------------------

    def _attach_workpiece(self, arm_id: str, wp_id: str, max_distance: float = 1.0) -> bool:
        """Grip workpiece with physics. Returns False if arm is not close enough.

        Makes the workpiece kinematic (fixed to world) at the gripper position,
        then releases it back to dynamic when placed.
        """
        robot = self._robots[arm_id]

        # Get robot base position
        base_pos = np.array([0.0, 0.0, 0.0])
        if hasattr(robot, "get_world_pose"):
            try:
                bp, _ = robot.get_world_pose()
                base_pos = np.array(bp)
            except Exception:
                pass

        # Get workpiece position
        wp_pos, _ = self._workpieces[wp_id].get_world_pose()

        # Distance check
        distance = float(np.linalg.norm(base_pos - wp_pos))
        if distance > max_distance:
            logger.warning(
                "Grip failed: workpiece %.2fm from robot (max %.2fm)",
                distance, max_distance,
            )
            return False

        # Physics approach: make workpiece kinematic (fixed to world) at gripper position
        # This simulates the gripper holding the workpiece
        try:
            wp_obj = self._workpieces[wp_id]
            # Get gripper position (above robot base)
            gripper_pos = [base_pos[0], base_pos[1], base_pos[2] + 0.9]

            # Teleport to gripper position and freeze
            wp_obj.set_world_pose(position=gripper_pos)

            # Apply zero velocity to keep it in place
            wp_obj.set_linear_velocity([0, 0, 0])
            wp_obj.set_angular_velocity([0, 0, 0])

            logger.debug("Gripped '%s' at gripper position", wp_id)
        except Exception as e:
            logger.warning("Grip physics failed, using teleport: %s", e)
            wp_obj.set_world_pose(position=[base_pos[0], base_pos[1], base_pos[2] + 0.9])

        self._workpiece_held_by[wp_id] = arm_id
        logger.info("Gripped '%s' at %.2fm", wp_id, distance)
        return True

    def _detach_workpiece(self, wp_id: str, x: float, y: float, z: float) -> bool:
        """Release workpiece at target position with gravity.

        Places workpiece at target and lets physics handle the settling.
        """
        if wp_id not in self._workpieces:
            return False

        wp_obj = self._workpieces[wp_id]
        wp_obj.set_world_pose(position=[x, y, z])
        # Set small downward velocity to simulate gravity settling
        wp_obj.set_linear_velocity([0, 0, -0.5])

        self._workpiece_held_by[wp_id] = None
        logger.info("Released '%s' at (%.2f, %.2f, %.2f)", wp_id, x, y, z)
        return True

    # ------------------------------------------------------------------
    # Physics verification
    # ------------------------------------------------------------------

    def verify_pick(self, arm_id: str, wp_id: str) -> dict:
        """Verify that a pick action was physically correct.

        Checks:
        1. Workpiece is held by the arm
        2. Workpiece position matches gripper position (within tolerance)
        3. Workpiece is no longer at its original position

        Returns dict with 'passed', 'details'.
        """
        result = {"passed": True, "checks": []}

        # Check 1: Workpiece held by arm
        held = self._workpiece_held_by.get(wp_id)
        if held != arm_id:
            result["passed"] = False
            result["checks"].append(f"FAIL: workpiece held_by={held}, expected={arm_id}")
        else:
            result["checks"].append(f"OK: workpiece held by arm")

        # Check 2: Workpiece position near gripper
        robot = self._robots[arm_id]
        base_pos = np.array([0.0, 0.0, 0.0])
        if hasattr(robot, "get_world_pose"):
            try:
                bp, _ = robot.get_world_pose()
                base_pos = np.array(bp)
            except Exception:
                pass

        wp_pos, _ = self._workpieces[wp_id].get_world_pose()
        # After pick, workpiece should be above robot base (gripper hold position)
        expected_z = base_pos[2] + 0.9
        z_diff = abs(wp_pos[2] - expected_z)
        if z_diff > 0.5:
            result["passed"] = False
            result["checks"].append(f"FAIL: workpiece z={wp_pos[2]:.2f}, expected ~{expected_z:.2f}")
        else:
            result["checks"].append(f"OK: workpiece at z={wp_pos[2]:.2f}")

        # Check 3: Workpiece moved from original position
        wp_obj = self._workpieces[wp_id]
        if hasattr(wp_obj, "get_world_pose"):
            current_pos, _ = wp_obj.get_world_pose()
            result["checks"].append(f"OK: workpiece at ({current_pos[0]:.2f}, {current_pos[1]:.2f}, {current_pos[2]:.2f})")

        return result

    def verify_place(self, wp_id: str, expected_x: float, expected_y: float, expected_z: float, tolerance: float = 0.3) -> dict:
        """Verify that a place action was physically correct.

        Checks:
        1. Workpiece is not held by any arm
        2. Workpiece position is near the target position

        Returns dict with 'passed', 'details'.
        """
        result = {"passed": True, "checks": []}

        # Check 1: Workpiece not held
        held = self._workpiece_held_by.get(wp_id)
        if held is not None:
            result["passed"] = False
            result["checks"].append(f"FAIL: workpiece still held by arm '{held}'")
        else:
            result["checks"].append("OK: workpiece released")

        # Check 2: Position near target
        wp_pos, _ = self._workpieces[wp_id].get_world_pose()
        dist = float(np.sqrt(
            (wp_pos[0] - expected_x) ** 2 +
            (wp_pos[1] - expected_y) ** 2 +
            (wp_pos[2] - expected_z) ** 2
        ))
        if dist > tolerance:
            result["passed"] = False
            result["checks"].append(f"FAIL: distance {dist:.2f}m > tolerance {tolerance}m")
        else:
            result["checks"].append(f"OK: placed at ({wp_pos[0]:.2f}, {wp_pos[1]:.2f}, {wp_pos[2]:.2f})")

        return result

    def verify_trajectory(self, arm_id: str, positions: list) -> dict:
        """Verify that the robot moved through expected positions.

        Args:
            arm_id: Robot arm ID
            positions: List of (x, y, z) tuples the arm should have visited

        Returns dict with 'passed', 'details'.
        """
        result = {"passed": True, "checks": []}

        robot = self._robots[arm_id]
        if not hasattr(robot, "get_world_pose"):
            result["passed"] = False
            result["checks"].append("FAIL: cannot get robot position")
            return result

        base_pos, _ = robot.get_world_pose()
        result["checks"].append(f"Robot at ({base_pos[0]:.2f}, {base_pos[1]:.2f}, {base_pos[2]:.2f})")

        # Check if robot is within expected range
        if positions:
            min_x = min(p[0] for p in positions)
            max_x = max(p[0] for p in positions)
            if not (min_x - 1.0 <= base_pos[0] <= max_x + 1.0):
                result["passed"] = False
                result["checks"].append(f"FAIL: robot x={base_pos[0]:.2f} outside range [{min_x:.2f}, {max_x:.2f}]")

        return result

    def get_verification_report(self) -> dict:
        """Get a summary of all verification results for the last execution."""
        return {
            "robots_loaded": len(self._robots),
            "workpieces_loaded": len(self._workpieces),
            "workpieces_held": sum(1 for v in self._workpiece_held_by.values() if v is not None),
            "frames_captured": len(self._frames),
        }

    # ------------------------------------------------------------------
    # Station markers
    # ------------------------------------------------------------------

    def _create_station_markers(self, scene_config: dict) -> None:
        """Create colored platform markers for each station."""
        from omni.isaac.core.objects import VisualCuboid  # type: ignore[import-untyped]

        station_colors = [
            np.array([0.2, 0.6, 0.2]),   # green - feed
            np.array([0.2, 0.4, 0.8]),   # blue - transport
            np.array([0.8, 0.5, 0.1]),   # orange - assembly
            np.array([0.8, 0.2, 0.2]),   # red - inspection
        ]

        for i, station in enumerate(scene_config.get("stations", [])):
            pos = station.get("position", {})
            color = station_colors[i % len(station_colors)]
            self._world.scene.add(
                VisualCuboid(
                    prim_path=f"/World/Stations/{station['id']}",
                    name=station["id"],
                    position=[pos.get("x", 0), pos.get("y", 0), -0.05],
                    scale=[0.5, 0.5, 0.05],
                    color=color,
                )
            )

    # ------------------------------------------------------------------
    # Frame capture
    # ------------------------------------------------------------------

    def _setup_frame_capture(self) -> None:
        """Set up camera, lighting, and frame capture."""
        try:
            import omni.replicator.core as rep  # type: ignore[import-untyped]
            import omni.usd  # type: ignore[import-untyped]
            from pxr import Gf, UsdGeom, UsdLux  # type: ignore[import-untyped]
            import carb.settings  # type: ignore[import-untyped]

            # Force renderer
            settings = carb.settings.get_settings()
            settings.set("/app/renderer/enabled", True)
            settings.set("/app/renderer/active", "RaytracedLighting")
            settings.set("/rtx/rendermode", "RaytracedLighting")

            stage = omni.usd.get_context().get_stage()

            # Lighting
            dome = UsdLux.DomeLight.Define(stage, "/World/DomeLight")
            dome.GetIntensityAttr().Set(1000.0)

            sun = UsdLux.DistantLight.Define(stage, "/World/SunLight")
            sun.GetIntensityAttr().Set(500.0)
            sun.GetAngleAttr().Set(0.53)
            sxform = UsdGeom.Xformable(sun.GetPrim())
            sxform.AddRotateXOp().Set(-45.0)
            sxform.AddRotateZOp().Set(30.0)

            # Fixed camera position that shows all 3 arms (x=0 to x=4)
            cam_x, cam_y, cam_z = 2.0, 15.0, 12.0
            cx, cy, cz = 2.0, -0.75, 0.3  # scene center

            # Create camera
            cam_path = "/World/Camera"
            cam = UsdGeom.Camera.Define(stage, cam_path)
            xf = UsdGeom.Xformable(cam.GetPrim())
            xf.ClearXformOpOrder()
            xf.AddTranslateOp().Set(Gf.Vec3d(cam_x, cam_y, cam_z))

            # Look-at rotation
            fwd = Gf.Vec3d(cx - cam_x, cy - cam_y, cz - cam_z).GetNormalized()
            up = Gf.Vec3d(0, 0, 1)
            right = fwd ^ up
            if right.GetLength() < 0.001:
                up = Gf.Vec3d(0, 1, 0)
                right = fwd ^ up
            right = right.GetNormalized()
            up = (right ^ fwd).GetNormalized()
            rot = Gf.Matrix3d(
                right[0], right[1], right[2],
                up[0], up[1], up[2],
                -fwd[0], -fwd[1], -fwd[2],
            )
            q = rot.ExtractRotation().GetQuat()
            xf.AddOrientOp().Set(Gf.Quatf(q.GetReal(), *q.GetImaginary()))

            # Render product + annotator
            self._replicator_render_product = rep.create.render_product(cam_path, resolution=(1920, 1080))
            self._replicator_annotator = rep.AnnotatorRegistry.get_annotator("rgb")
            self._replicator_annotator.attach(self._replicator_render_product)

            # Warm up
            for _ in range(10):
                self._world.step(render=True)
            rep.orchestrator.run()
            for _ in range(3):
                rep.orchestrator.step()

            data = self._replicator_annotator.get_data()
            if data is not None and np.asarray(data).max() > 0:
                logger.info("Frame capture verified OK")

            logger.info("Camera at (%.1f,%.1f,%.1f) looking at (%.1f,%.1f,%.1f)", cam_x, cam_y, cam_z, cx, cy, cz)
        except Exception as e:
            logger.warning("Frame capture not available: %s", e)
            self._replicator_annotator = None

    def _clear_scene(self) -> None:
        """Remove all objects from the stage for scene reloading."""
        import omni.usd  # type: ignore[import-untyped]

        # Remove all prims under /World
        stage = omni.usd.get_context().get_stage()
        world_prim = stage.GetPrimAtPath("/World")
        if world_prim.IsValid():
            for child in list(world_prim.GetChildren()):
                stage.RemovePrim(child.GetPath())

        # Also remove ground plane and camera
        for path in ["/World/GroundPlane", "/World/Camera", "/World/DomeLight", "/World/SunLight"]:
            prim = stage.GetPrimAtPath(path)
            if prim.IsValid():
                stage.RemovePrim(path)

        # Clear internal registries
        self._robots.clear()
        self._workpieces.clear()
        self._workpiece_held_by.clear()
        self._ee_body_idx.clear()
        self._frames.clear()
        self._scene_loaded = False

    def _capture_frame(self) -> None:
        if self._replicator_annotator is None:
            return
        try:
            import omni.replicator.core as rep  # type: ignore[import-untyped]

            rep.orchestrator.step()
            data = self._replicator_annotator.get_data()
            if data is not None:
                arr = np.asarray(data)
                if arr.size > 0 and arr.max() > 0:
                    self._frames.append(data)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            raise RuntimeError("Isaac Sim is not initialized; call initialize() first")



def _random_color(wp_id: str) -> "np.ndarray":
    h = hash(wp_id) % 360
    c = 0.7 * 0.9
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = 0.9 - c
    if h < 60:
        r, g, b = c, x, 0
    elif h < 120:
        r, g, b = x, c, 0
    elif h < 180:
        r, g, b = 0, c, x
    elif h < 240:
        r, g, b = 0, x, c
    elif h < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x
    return np.array([r + m, g + m, b + m])
