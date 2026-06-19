"""
Prompt templates for executable code generation.

These prompts instruct the LLM to generate (and refine) Python code for
robot arm tasks using a standard set of atomic primitives.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Atomic primitives reference (included in prompts)
# ---------------------------------------------------------------------------

PRIMITIVES_REFERENCE: str = """\
## Available Atomic Primitives

The generated code must use the following primitive functions.  They are \
imported from ``robot_primitives`` and are available in the execution \
environment:

| Function | Signature | Description |
|---|---|---|
| `move_to` | `move_to(arm_id: str, x: float, y: float, z: float, speed: float = 1.0) -> bool` | Move the arm end-effector to the given Cartesian position. Returns success. |
| `grip` | `grip(arm_id: str, force: float = 50.0, object_id: str | None = None) -> bool` | Close the gripper with specified force (Newtons). Returns success. |
| `release` | `release(arm_id: str, object_id: str | None = None) -> bool` | Open the gripper / release held object. Returns success. |
| `rotate` | `rotate(arm_id: str, roll: float = 0.0, pitch: float = 0.0, yaw: float = 0.0, speed: float = 1.0) -> bool` | Rotate the end-effector by the given Euler angles (degrees). Returns success. |
| `linear_move` | `linear_move(arm_id: str, dx: float, dy: float, dz: float, speed: float = 0.5) -> bool` | Move the end-effector by a relative linear displacement (mm). Returns success. |
| `wait` | `wait(seconds: float) -> None` | Pause execution for the given duration. |
| `check_sensor` | `check_sensor(arm_id: str, sensor_type: str, threshold: float | None = None) -> dict` | Read a sensor (e.g. `"force"`, `"proximity"`, `"camera"`). Returns a dict with `value` and `status`. |"""

CODE_GENERATE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "code": {
            "type": "string",
            "description": (
                "Complete, executable Python code for the task.  Must define "
                "a function `execute(arm_id: str) -> dict` that returns a "
                "result dict with at least a 'success' key."
            ),
        },
        "explanation": {
            "type": "string",
            "description": "Brief explanation of the generated code.",
        },
        "primitives_used": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of atomic primitive names used.",
        },
        "estimated_duration": {
            "type": "number",
            "description": "Estimated runtime in seconds.",
        },
        "error_handling": {
            "type": "string",
            "description": "Summary of how errors are handled.",
        },
    },
    "required": [
        "code",
        "explanation",
        "primitives_used",
        "estimated_duration",
    ],
}

CODE_REFINE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "refined_code": {
            "type": "string",
            "description": "The improved executable Python code.",
        },
        "changes_made": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of specific changes made.",
        },
        "explanation": {
            "type": "string",
            "description": "Why the changes improve the code.",
        },
        "primitives_used": {
            "type": "array",
            "items": {"type": "string"},
        },
        "estimated_duration": {
            "type": "number",
        },
    },
    "required": [
        "refined_code",
        "changes_made",
        "explanation",
        "primitives_used",
        "estimated_duration",
    ],
}


# ---------------------------------------------------------------------------
# CODE_GENERATE_PROMPT
# ---------------------------------------------------------------------------


def code_generate_prompt(
    task_name: str,
    task_description: str,
    operation_type: str,
    parameters: Dict[str, Any],
    arm_id: str,
    arm_capabilities: List[str],
    constraints: List[str] | None = None,
    environment_context: str | None = None,
) -> str:
    """Build the prompt that generates executable Python code for a task.

    Parameters
    ----------
    task_name:
        Short name of the task.
    task_description:
        Detailed description of what the task should accomplish.
    operation_type:
        The high-level operation type (e.g. ``"pick"``, ``"place"``).
    parameters:
        Operation-specific parameters (target position, object id, etc.).
    arm_id:
        The robot arm ID that will execute this code.
    arm_capabilities:
        List of capabilities the assigned arm has.
    constraints:
        Optional list of constraints (speed limits, safety zones, etc.).
    environment_context:
        Optional description of the workspace / objects in the scene.

    Returns
    -------
    str
        A fully formatted prompt string.
    """
    params_json = json.dumps(parameters, indent=2)

    constraints_section = ""
    if constraints:
        bullet_list = "\n".join(f"   - {c}" for c in constraints)
        constraints_section = f"\n\n## Constraints\n{bullet_list}"

    env_section = ""
    if environment_context:
        env_section = f"\n\n## Environment Context\n{environment_context}"

    return f"""\
You are an expert robotics code generator.  Write executable Python code \
for a robot arm task using the available atomic primitives.

{PRIMITIVES_REFERENCE}

## Task Specification

- **Name**: {task_name}
- **Description**: {task_description}
- **Operation Type**: {operation_type}
- **Assigned Arm ID**: `{arm_id}`
- **Arm Capabilities**: {', '.join(arm_capabilities)}

## Task Parameters
```json
{params_json}
```
{constraints_section}
{env_section}

## Code Requirements

1. Define a function `execute(arm_id: str) -> dict` that performs the task.
2. The return dict MUST include at least `'success': bool`.  Include \
additional result fields as appropriate (e.g. `'object_grasped'`, \
`'final_position'`).
3. Use ONLY the atomic primitives listed above.  Do NOT use external \
libraries except basic Python (`math`, `time`, `logging`).
4. Include proper error handling: check return values of primitives and \
handle failures gracefully.
5. Add logging calls at key steps for traceability.
6. Include docstrings.
7. The code must be syntactically valid Python 3.10+.

## Output Format

Respond with a single JSON object matching this schema:

```json
{json.dumps(CODE_GENERATE_SCHEMA, indent=2)}
```

Do NOT include any commentary outside the JSON object."""


# ---------------------------------------------------------------------------
# CODE_REFINE_PROMPT
# ---------------------------------------------------------------------------


def code_refine_prompt(
    original_code: str,
    feedback: str,
    task_name: str,
    task_description: str,
    operation_type: str,
    arm_id: str,
    error_log: str | None = None,
    test_results: Dict[str, Any] | None = None,
) -> str:
    """Build the prompt that refines generated code based on feedback.

    Parameters
    ----------
    original_code:
        The code that needs to be refined.
    feedback:
        Natural-language feedback describing what went wrong or what should
        be improved.
    task_name:
        Name of the task the code implements.
    task_description:
        Description of the task.
    operation_type:
        The operation type.
    arm_id:
        The robot arm ID.
    error_log:
        Optional stack trace or error output from a failed execution.
    test_results:
        Optional dict of test results (e.g.
        ``{"test_position_accuracy": {"passed": False, "actual": ..., "expected": ...}}``).

    Returns
    -------
    str
        A fully formatted prompt string.
    """
    error_section = ""
    if error_log:
        error_section = f"\n\n## Error Log\n```\n{error_log}\n```"

    test_section = ""
    if test_results:
        test_json = json.dumps(test_results, indent=2)
        test_section = f"\n\n## Test Results\n```json\n{test_json}\n```"

    return f"""\
You are an expert robotics code reviewer and fixer.  Given existing code, \
feedback, and (optionally) error logs, produce a corrected and improved \
version of the code.

{PRIMITIVES_REFERENCE}

## Original Code
```python
{original_code}
```

## Task Context

- **Name**: {task_name}
- **Description**: {task_description}
- **Operation Type**: {operation_type}
- **Arm ID**: `{arm_id}`

## Feedback
{feedback}
{error_section}
{test_section}

## Refinement Instructions

1. Address ALL issues mentioned in the feedback.
2. If there are errors, fix the root cause (not just the symptom).
3. Maintain the same function signature: `execute(arm_id: str) -> dict`.
4. Preserve any correct logic; only change what is necessary.
5. Improve error handling and logging if they are insufficient.
6. Ensure the code is syntactically valid Python 3.10+.

## Output Format

Respond with a single JSON object matching this schema:

```json
{json.dumps(CODE_REFINE_SCHEMA, indent=2)}
```

Do NOT include any commentary outside the JSON object."""
