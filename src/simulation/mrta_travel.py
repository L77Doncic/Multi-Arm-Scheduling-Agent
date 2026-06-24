"""
MRTA Travel Time Module

Loads and manages travel time matrices from MRTA-Benchmark data.
Used to calculate realistic movement times between stations.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MRATravelTimeManager:
    """
    Manages travel time data from MRTA-Benchmark.

    The MRTA-Benchmark provides:
    - T_e: Task execution times (how long each task takes)
    - T_t: Travel time matrix (time to move between locations)
    """

    def __init__(self):
        self._travel_times: Dict[str, Dict] = {}
        self._current_scenario: Optional[str] = None

    def load_scenario(self, scenario_config: dict) -> None:
        """
        Load MRTA travel times from scenario configuration.

        Args:
            scenario_config: Dictionary containing mrta_travel_times
        """
        # Try to get mrta_data from different possible locations
        mrta_data = scenario_config.get('mrta_travel_times')
        if not mrta_data and 'scenario' in scenario_config:
            mrta_data = scenario_config.get('scenario', {}).get('mrta_travel_times')
        if not mrta_data:
            mrta_data = scenario_config.get('mrta_travel_times')

        if mrta_data:
            self._travel_times = {
                'T_e': mrta_data.get('T_e', []),
                'T_t': mrta_data.get('T_t', []),
                'task_locations': mrta_data.get('task_locations', []),
                'precedence_constraints': mrta_data.get('precedence_constraints', [])
            }
            self._current_scenario = scenario_config.get('name') or scenario_config.get('scenario', {}).get('name', 'unknown')
            logger.info("Loaded MRTA travel times for scenario: %s", self._current_scenario)
        else:
            logger.warning("No MRTA travel times in scenario config")

    def get_travel_time(self, from_location: int, to_location: int) -> float:
        """
        Get travel time between two locations.

        Args:
            from_location: Source location index
            to_location: Target location index

        Returns:
            Travel time in seconds
        """
        if not self._travel_times or 'T_t' not in self._travel_times:
            return 0.0

        T_t = self._travel_times['T_t']
        if from_location < len(T_t) and to_location < len(T_t[from_location]):
            return T_t[from_location][to_location]
        return 0.0

    def get_task_execution_time(self, task_id: int) -> float:
        """
        Get execution time for a task from MRTA data.

        Args:
            task_id: Task index

        Returns:
            Execution time in seconds
        """
        if not self._travel_times or 'T_e' not in self._travel_times:
            return 0.0

        T_e = self._travel_times['T_e']
        if task_id < len(T_e):
            return T_e[task_id]
        return 0.0

    def get_task_location(self, task_id: int) -> Optional[int]:
        """
        Get the location where a task is performed.

        Args:
            task_id: Task index

        Returns:
            Location index or None
        """
        if not self._travel_times or 'task_locations' not in self._travel_times:
            return None

        locations = self._travel_times['task_locations']
        if task_id < len(locations):
            return locations[task_id]
        return None

    def calculate_total_time(
        self,
        task_id: int,
        current_location: int,
        task_location: int
    ) -> Tuple[float, float, float]:
        """
        Calculate total time for a task including travel and execution.

        Args:
            task_id: Task index
            current_location: Current robot location
            task_location: Where the task needs to be performed

        Returns:
            Tuple of (travel_time, execution_time, total_time)
        """
        travel_time = self.get_travel_time(current_location, task_location)
        execution_time = self.get_task_execution_time(task_id)
        total_time = travel_time + execution_time

        return travel_time, execution_time, total_time

    def get_statistics(self) -> Dict:
        """Get statistics about travel times."""
        if not self._travel_times:
            return {}

        T_e = self._travel_times.get('T_e', [])
        T_t = self._travel_times.get('T_t', [])

        # Task execution stats
        task_times = [t for t in T_e if t > 0]
        avg_task_time = sum(task_times) / len(task_times) if task_times else 0

        # Travel time stats
        travel_times = [t for row in T_t for t in row if t > 0]
        avg_travel_time = sum(travel_times) / len(travel_times) if travel_times else 0
        max_travel_time = max(travel_times) if travel_times else 0

        return {
            'scenario': self._current_scenario,
            'num_tasks': len(T_e),
            'avg_task_time': avg_task_time,
            'avg_travel_time': avg_travel_time,
            'max_travel_time': max_travel_time,
            'travel_time_ratio': avg_travel_time / (avg_task_time + avg_travel_time) if (avg_task_time + avg_travel_time) > 0 else 0
        }


# Global instance
_travel_manager = MRATravelTimeManager()


def get_travel_manager() -> MRATravelTimeManager:
    """Get the global travel time manager."""
    return _travel_manager
