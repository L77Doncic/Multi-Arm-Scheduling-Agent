"""
Scene builder for constructing simulation environments programmatically.

Provides a fluent API for assembling scenes with workstations, conveyors,
workpieces, and robot arms, as well as convenience factory methods for
common topologies such as assembly lines.
"""

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)


def _make_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


# ------------------------------------------------------------------
# Data classes
# ------------------------------------------------------------------

@dataclass
class Workstation:
    """A fixed workstation in the scene."""
    id: str
    position: Dict[str, float]
    capabilities: List[str] = field(default_factory=list)
    queue: List[str] = field(default_factory=list)  # workpiece ids waiting


@dataclass
class Conveyor:
    """A conveyor belt connecting two points."""
    id: str
    start: Dict[str, float]
    end: Dict[str, float]
    speed: float = 1.0  # m/s


@dataclass
class Workpiece:
    """A workpiece / object that can be manipulated."""
    id: str
    type: str
    position: Dict[str, float] = field(default_factory=dict)
    status: str = "waiting"  # waiting | in_progress | done


@dataclass
class RobotArm:
    """A robot arm placed in the scene."""
    id: str
    position: Dict[str, float] = field(default_factory=dict)
    capabilities: List[str] = field(default_factory=list)


@dataclass
class Bounds:
    """Axis-aligned bounding box for the scene."""
    x_min: float = -10.0
    x_max: float = 10.0
    y_min: float = -10.0
    y_max: float = 10.0
    z_min: float = 0.0
    z_max: float = 5.0


@dataclass
class Scene:
    """A fully described simulation scene."""
    workstations: List[Workstation] = field(default_factory=list)
    conveyors: List[Conveyor] = field(default_factory=list)
    workpieces: List[Workpiece] = field(default_factory=list)
    robot_arms: List[RobotArm] = field(default_factory=list)
    bounds: Bounds = field(default_factory=Bounds)


# ------------------------------------------------------------------
# SceneBuilder
# ------------------------------------------------------------------

class SceneBuilder:
    """
    Incrementally construct a :class:`Scene`.

    Typical usage::

        builder = SceneBuilder()
        builder.add_workstation(position={"x": 0, "y": 0, "z": 0},
                                capabilities=["pick", "place"])
        scene = builder.build()
    """

    def __init__(self) -> None:
        self._workstations: List[Workstation] = []
        self._conveyors: List[Conveyor] = []
        self._workpieces: List[Workpiece] = []
        self._robot_arms: List[RobotArm] = []
        self._bounds = Bounds()

    # ------------------------------------------------------------------
    # Fluent builder methods
    # ------------------------------------------------------------------

    def add_workstation(
        self,
        position: Dict[str, float],
        capabilities: Optional[List[str]] = None,
        station_id: Optional[str] = None,
    ) -> "SceneBuilder":
        """Add a workstation and return *self* for chaining."""
        ws = Workstation(
            id=station_id or _make_id("station"),
            position=position,
            capabilities=capabilities or [],
        )
        self._workstations.append(ws)
        logger.debug("Added workstation %s at %s", ws.id, position)
        return self

    def add_conveyor(
        self,
        start: Dict[str, float],
        end: Dict[str, float],
        speed: float = 1.0,
        conveyor_id: Optional[str] = None,
    ) -> "SceneBuilder":
        """Add a conveyor belt and return *self* for chaining."""
        conv = Conveyor(
            id=conveyor_id or _make_id("conveyor"),
            start=start,
            end=end,
            speed=speed,
        )
        self._conveyors.append(conv)
        logger.debug("Added conveyor %s", conv.id)
        return self

    def add_workpiece(
        self,
        position: Dict[str, float],
        workpiece_type: str = "generic",
        workpiece_id: Optional[str] = None,
    ) -> "SceneBuilder":
        """Add a workpiece and return *self* for chaining."""
        wp = Workpiece(
            id=workpiece_id or _make_id("wp"),
            type=workpiece_type,
            position=position,
        )
        self._workpieces.append(wp)
        logger.debug("Added workpiece %s (%s)", wp.id, workpiece_type)
        return self

    def set_bounds(self, bounds: Bounds) -> "SceneBuilder":
        self._bounds = bounds
        return self

    def build(self) -> Scene:
        """Return the assembled :class:`Scene`."""
        scene = Scene(
            workstations=list(self._workstations),
            conveyors=list(self._conveyors),
            workpieces=list(self._workpieces),
            robot_arms=list(self._robot_arms),
            bounds=self._bounds,
        )
        logger.info(
            "Built scene: %d stations, %d conveyors, %d workpieces, %d arms",
            len(scene.workstations),
            len(scene.conveyors),
            len(scene.workpieces),
            len(scene.robot_arms),
        )
        return scene

    # ------------------------------------------------------------------
    # Factory helpers
    # ------------------------------------------------------------------

    def build_assembly_line(
        self,
        num_stations: int = 3,
        num_workpieces: int = 5,
        num_arms: int = 2,
    ) -> Scene:
        """
        Construct a linear assembly line scene.

        Stations are equally spaced along the X axis.  A single
        conveyor runs the full length.  Arms are placed between
        adjacent stations.

        Args:
            num_stations: Number of workstations (>= 1).
            num_workpieces: Number of workpieces to scatter.
            num_arms: Number of robot arms (>= 1).

        Returns:
            A fully populated :class:`Scene`.
        """
        num_stations = max(1, num_stations)
        num_arms = max(1, num_arms)

        station_spacing = 2.0
        y_offset = 0.0
        z_height = 0.0

        # Workstations
        station_positions: List[Dict[str, float]] = []
        for i in range(num_stations):
            pos = {"x": i * station_spacing, "y": y_offset, "z": z_height}
            station_positions.append(pos)
            self.add_workstation(
                position=pos,
                capabilities=["pick", "place", "assemble"],
                station_id=f"station_{i}",
            )

        # Conveyor from first to last station
        if num_stations >= 2:
            self.add_conveyor(
                start=station_positions[0],
                end=station_positions[-1],
                speed=0.5,
                conveyor_id="main_conveyor",
            )

        # Robot arms -- place them alternating on +Y / -Y sides
        for i in range(num_arms):
            idx = i % num_stations
            side = 1.0 if i % 2 == 0 else -1.0
            pos = {
                "x": station_positions[idx]["x"],
                "y": station_positions[idx]["y"] + side * 1.0,
                "z": z_height,
            }
            self._robot_arms.append(
                RobotArm(
                    id=f"arm_{i}",
                    position=pos,
                    capabilities=["pick", "place", "move", "assemble", "inspect"],
                )
            )

        # Workpieces -- scatter near stations
        for i in range(num_workpieces):
            idx = i % num_stations
            pos = {
                "x": station_positions[idx]["x"] + 0.3,
                "y": station_positions[idx]["y"] + 0.3,
                "z": z_height + 0.05,
            }
            self.add_workpiece(
                position=pos,
                workpiece_type="part",
                workpiece_id=f"wp_{i}",
            )

        return self.build()

    # ------------------------------------------------------------------
    # Config-based builder
    # ------------------------------------------------------------------

    def build_from_config(self, config: dict) -> Scene:
        """
        Build a scene from a configuration dictionary.

        Expected keys (all optional):
        - ``workstations``: list of workstation dicts
        - ``conveyors``: list of conveyor dicts
        - ``workpieces``: list of workpiece dicts
        - ``robot_arms``: list of robot-arm dicts
        - ``bounds``: dict with ``x_min``, ``x_max``, ``y_min``, ``y_max``, ``z_min``, ``z_max``

        Returns:
            A fully populated :class:`Scene`.
        """
        for ws_cfg in config.get("workstations", []):
            self.add_workstation(
                position=ws_cfg.get("position", {}),
                capabilities=ws_cfg.get("capabilities", []),
                station_id=ws_cfg.get("id"),
            )

        for conv_cfg in config.get("conveyors", []):
            self.add_conveyor(
                start=conv_cfg.get("start", {}),
                end=conv_cfg.get("end", {}),
                speed=conv_cfg.get("speed", 1.0),
                conveyor_id=conv_cfg.get("id"),
            )

        for wp_cfg in config.get("workpieces", []):
            self.add_workpiece(
                position=wp_cfg.get("position", {}),
                workpiece_type=wp_cfg.get("type", "generic"),
                workpiece_id=wp_cfg.get("id"),
            )

        for arm_cfg in config.get("robot_arms", []):
            self._robot_arms.append(
                RobotArm(
                    id=arm_cfg["id"],
                    position=arm_cfg.get("position", {}),
                    capabilities=arm_cfg.get("capabilities", []),
                )
            )

        bounds_cfg = config.get("bounds")
        if bounds_cfg:
            self._bounds = Bounds(
                x_min=bounds_cfg.get("x_min", -10.0),
                x_max=bounds_cfg.get("x_max", 10.0),
                y_min=bounds_cfg.get("y_min", -10.0),
                y_max=bounds_cfg.get("y_max", 10.0),
                z_min=bounds_cfg.get("z_min", 0.0),
                z_max=bounds_cfg.get("z_max", 5.0),
            )

        return self.build()
