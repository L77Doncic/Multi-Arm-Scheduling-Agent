"""
Prompt templates for task decomposition.

These prompts instruct the LLM to break down a natural-language instruction
into structured subtasks with dependencies, required capabilities, and
estimated durations.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Schema used by both prompts
# ---------------------------------------------------------------------------

TASK_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "tasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "Unique task identifier, e.g. 'task_0001'.",
                    },
                    "name": {
                        "type": "string",
                        "description": "Short human-readable task name.",
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed description of what the task does.",
                    },
                    "operation_type": {
                        "type": "string",
                        "enum": [
                            "pick",
                            "place",
                            "move",
                            "assemble",
                            "inspect",
                            "tighten",
                            "weld",
                            "paint",
                            "wait",
                            "check",
                        ],
                    },
                    "parameters": {
                        "type": "object",
                        "description": (
                            "Operation-specific parameters such as target "
                            "position, object name, tool settings, etc."
                        ),
                    },
                    "dependencies": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "IDs of tasks that must complete before this "
                            "task can start."
                        ),
                    },
                    "estimated_duration": {
                        "type": "number",
                        "description": "Estimated duration in seconds.",
                    },
                    "required_capabilities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Robot arm capabilities needed, e.g. "
                            "'gripper', 'vision', 'force_control'."
                        ),
                    },
                },
                "required": [
                    "id",
                    "name",
                    "description",
                    "operation_type",
                    "parameters",
                    "dependencies",
                    "estimated_duration",
                    "required_capabilities",
                ],
            },
        },
    },
    "required": ["tasks"],
}


# ---------------------------------------------------------------------------
# TASK_DECOMPOSE_PROMPT
# ---------------------------------------------------------------------------


def task_decompose_prompt(
    instruction: str,
    available_capabilities: List[str] | None = None,
    context: str | None = None,
) -> str:
    """Build the prompt that decomposes a natural-language instruction into
    structured subtasks.

    Parameters
    ----------
    instruction:
        The natural-language instruction describing the overall goal.
    available_capabilities:
        Optional list of capability keywords that robot arms in the system
        actually support (e.g. ``["gripper", "vision", "welding_tool"]``).
    context:
        Optional additional context such as environment description,
        constraints, or previous task history.

    Returns
    -------
    str
        A fully formatted prompt string ready to pass to an LLM.
    """
    capabilities_section = ""
    if available_capabilities:
        cap_list = ", ".join(f"'{c}'" for c in available_capabilities)
        capabilities_section = (
            f"\n\n## Available Robot Capabilities\n"
            f"The following capabilities are available in the system: "
            f"{cap_list}.\n"
            f"Only assign capabilities from this list to tasks."
        )

    context_section = ""
    if context:
        context_section = f"\n\n## Additional Context\n{context}"

    return f"""\
You are an expert robotics task planner.  Your job is to decompose a high-level \
natural-language instruction into a sequence of fine-grained subtasks that can \
be executed by one or more robotic arms.

## Instruction
{instruction}
{capabilities_section}
{context_section}

## Requirements

1. **Granularity** – Each subtask should correspond to exactly one atomic \
robot operation (e.g. a single pick, a single move, a single inspection).
2. **Dependencies** – Clearly specify which tasks must complete before others \
can begin.  Tasks with no mutual dependencies can run in parallel.
3. **Capabilities** – For every task, list the robot capabilities required \
(e.g. gripper, vision, force_control).
4. **Duration** – Provide a realistic duration estimate in seconds.
5. **Parameters** – Include all operation-specific parameters (target \
positions, object identifiers, tool settings, tolerances, etc.).
6. **IDs** – Use sequential IDs in the format ``task_NNNN`` (e.g. \
``task_0001``, ``task_0002``).

## Output Format

Respond with a single JSON object matching this schema:

```json
{json.dumps(TASK_SCHEMA, indent=2)}
```

Do NOT include any commentary outside the JSON object."""


# ---------------------------------------------------------------------------
# DEPENDENCY_ANALYSIS_PROMPT
# ---------------------------------------------------------------------------


DEPENDENCY_ANALYSIS_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "dependencies": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "depends_on": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "dependency_type": {
                        "type": "string",
                        "enum": [
                            "temporal",
                            "resource",
                            "data",
                            "causal",
                        ],
                    },
                    "reason": {"type": "string"},
                },
                "required": [
                    "task_id",
                    "depends_on",
                    "dependency_type",
                    "reason",
                ],
            },
        },
        "parallelizable_groups": {
            "type": "array",
            "items": {
                "type": "array",
                "items": {"type": "string"},
            },
            "description": (
                "Groups of task IDs that can execute simultaneously."
            ),
        },
        "critical_path": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Task IDs on the critical path (longest chain).",
        },
    },
    "required": ["dependencies", "parallelizable_groups", "critical_path"],
}


def dependency_analysis_prompt(
    tasks: List[Dict[str, Any]],
    environment_description: str | None = None,
) -> str:
    """Build the prompt that analyzes dependencies between decomposed tasks.

    Parameters
    ----------
    tasks:
        A list of task dictionaries (as produced by the decomposition step).
        Each should have at least ``id``, ``name``, ``description``, and
        ``operation_type``.
    environment_description:
        Optional textual description of the workspace, including object
        positions, shared resources, and physical constraints.

    Returns
    -------
    str
        A fully formatted prompt string.
    """
    task_list_str = json.dumps(tasks, indent=2)

    env_section = ""
    if environment_description:
        env_section = (
            f"\n\n## Environment Description\n{environment_description}"
        )

    return f"""\
You are an expert robotics scheduling analyst.  Given a list of decomposed \
tasks, analyze all dependencies between them.

## Tasks
```json
{task_list_str}
```
{env_section}

## Analysis Instructions

1. For each task, determine which other tasks it depends on and why.
2. Classify each dependency as one of:
   - **temporal** – Task B must happen after Task A (e.g. pick before place).
   - **resource** – Tasks compete for the same robot arm or tool.
   - **data** – Task B needs output produced by Task A.
   - **causal** – Task B physically requires the state created by Task A.
3. Identify groups of tasks that can run in parallel (no direct or indirect
   dependency between them).
4. Determine the **critical path** – the longest chain of dependent tasks
   that bounds the minimum overall execution time.

## Output Format

Respond with a single JSON object matching this schema:

```json
{json.dumps(DEPENDENCY_ANALYSIS_SCHEMA, indent=2)}
```

Do NOT include any commentary outside the JSON object."""
