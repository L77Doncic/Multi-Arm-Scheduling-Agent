"""
Prompt templates for resource allocation.

These prompts instruct the LLM to assign robot arms to tasks based on
capabilities, availability, and optimization objectives, and to resolve
resource conflicts when multiple tasks compete for the same arm.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Schema definitions
# ---------------------------------------------------------------------------

ALLOCATION_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "allocations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "The task being allocated.",
                    },
                    "arm_id": {
                        "type": "string",
                        "description": "The robot arm assigned to the task.",
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Why this arm was chosen.",
                    },
                    "estimated_start_time": {
                        "type": "number",
                        "description": "When the task can start (seconds from t=0).",
                    },
                    "estimated_end_time": {
                        "type": "number",
                        "description": "When the task is expected to finish.",
                    },
                },
                "required": [
                    "task_id",
                    "arm_id",
                    "reasoning",
                    "estimated_start_time",
                    "estimated_end_time",
                ],
            },
        },
        "unallocated_tasks": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Task IDs that could not be allocated (with reasons in notes).",
        },
        "makespan": {
            "type": "number",
            "description": "Total schedule length in seconds.",
        },
        "utilization": {
            "type": "object",
            "additionalProperties": {"type": "number"},
            "description": "Per-arm utilization ratio (0-1).",
        },
        "notes": {
            "type": "string",
            "description": "Any observations or warnings about the allocation.",
        },
    },
    "required": ["allocations", "unallocated_tasks", "makespan", "utilization"],
}

CONFLICT_RESOLVE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "resolution": {
            "type": "object",
            "properties": {
                "reassigned_tasks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string"},
                            "new_arm_id": {"type": "string"},
                            "new_start_time": {"type": "number"},
                            "reasoning": {"type": "string"},
                        },
                        "required": [
                            "task_id",
                            "new_arm_id",
                            "new_start_time",
                            "reasoning",
                        ],
                    },
                },
                "deferred_tasks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string"},
                            "defer_until": {"type": "number"},
                            "reasoning": {"type": "string"},
                        },
                        "required": ["task_id", "defer_until", "reasoning"],
                    },
                },
                "cancelled_tasks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string"},
                            "reasoning": {"type": "string"},
                        },
                        "required": ["task_id", "reasoning"],
                    },
                },
            },
            "required": ["reassigned_tasks", "deferred_tasks", "cancelled_tasks"],
        },
        "new_makespan": {
            "type": "number",
        },
        "notes": {
            "type": "string",
        },
    },
    "required": ["resolution", "new_makespan"],
}


# ---------------------------------------------------------------------------
# RESOURCE_ALLOCATE_PROMPT
# ---------------------------------------------------------------------------


def resource_allocate_prompt(
    tasks: List[Dict[str, Any]],
    robot_arms: List[Dict[str, Any]],
    optimization_goal: str = "minimize_makespan",
    constraints: List[str] | None = None,
) -> str:
    """Build the prompt that allocates robot arms to tasks.

    Parameters
    ----------
    tasks:
        List of task dicts with at least ``id``, ``name``,
        ``operation_type``, ``dependencies``, ``estimated_duration``, and
        ``required_capabilities``.
    robot_arms:
        List of arm dicts with at least ``id``, ``name``, and
        ``capabilities``.
    optimization_goal:
        One of ``"minimize_makespan"``, ``"maximize_utilization"``, or
        ``"balance_load"``.
    constraints:
        Optional list of additional constraint strings (e.g.
        ``"arm_01 must not be used for welding"``).

    Returns
    -------
    str
        A fully formatted prompt string.
    """
    tasks_json = json.dumps(tasks, indent=2)
    arms_json = json.dumps(robot_arms, indent=2)

    constraints_section = ""
    if constraints:
        bullet_list = "\n".join(f"   - {c}" for c in constraints)
        constraints_section = f"\n\n## Additional Constraints\n{bullet_list}"

    return f"""\
You are an expert multi-robot scheduling optimizer.  Given a set of tasks \
and available robot arms, produce an optimal allocation of arms to tasks.

## Tasks
```json
{tasks_json}
```

## Robot Arms
```json
{arms_json}
```

## Optimization Goal
{optimization_goal}
{constraints_section}

## Allocation Rules

1. **Capability matching** – A robot arm can only be assigned to a task if \
it possesses ALL of the task's ``required_capabilities``.
2. **Dependency ordering** – If task B depends on task A, B must start \
after A finishes (even if on the same arm).
3. **Single-task at a time** – A robot arm can only execute one task at a \
time.
4. **Parallelism** – Independent tasks SHOULD be assigned to different arms \
when possible to reduce makespan.

## Output Format

Respond with a single JSON object matching this schema:

```json
{json.dumps(ALLOCATION_SCHEMA, indent=2)}
```

Do NOT include any commentary outside the JSON object."""


# ---------------------------------------------------------------------------
# CONFLICT_RESOLVE_PROMPT
# ---------------------------------------------------------------------------


def conflict_resolve_prompt(
    conflicts: List[Dict[str, Any]],
    current_allocation: List[Dict[str, Any]],
    robot_arms: List[Dict[str, Any]],
    tasks: List[Dict[str, Any]],
) -> str:
    """Build the prompt that resolves resource conflicts.

    Parameters
    ----------
    conflicts:
        List of conflict dicts, each with ``task_id``, ``conflicting_task_id``,
        ``arm_id``, and ``conflict_type`` (e.g. ``"overlap"``,
        ``"capability_mismatch"``).
    current_allocation:
        The current allocation (list of allocation dicts).
    robot_arms:
        List of available robot arm dicts.
    tasks:
        Full task list for reference.

    Returns
    -------
    str
        A fully formatted prompt string.
    """
    conflicts_json = json.dumps(conflicts, indent=2)
    allocation_json = json.dumps(current_allocation, indent=2)
    arms_json = json.dumps(robot_arms, indent=2)
    tasks_json = json.dumps(tasks, indent=2)

    return f"""\
You are an expert robotics scheduling conflict resolver.  The current task \
allocation has resource conflicts that must be resolved.

## Detected Conflicts
```json
{conflicts_json}
```

## Current Allocation
```json
{allocation_json}
```

## Available Robot Arms
```json
{arms_json}
```

## All Tasks (for reference)
```json
{tasks_json}
```

## Resolution Instructions

For each conflict you may:
1. **Reassign** a task to a different arm that has the required capabilities \
and is available during the task's time window.
2. **Defer** a task to a later time slot on the same arm.
3. **Cancel** a task if it is infeasible given current resources (use only \
as a last resort).

Prioritise solutions that:
- Preserve the overall schedule makespan.
- Minimise the number of reassigned/deferred tasks.
- Respect all dependency constraints.

## Output Format

Respond with a single JSON object matching this schema:

```json
{json.dumps(CONFLICT_RESOLVE_SCHEMA, indent=2)}
```

Do NOT include any commentary outside the JSON object."""
