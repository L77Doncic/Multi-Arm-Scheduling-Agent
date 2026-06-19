"""
Task Decomposition Prompt Templates

This module provides prompt templates for decomposing natural language
instructions into structured tasks for multi-arm scheduling.
"""


class TaskDecompositionPrompts:
    """Prompt templates for task decomposition."""

    SYSTEM_PROMPT = """You are an expert in industrial robotics and task planning.
Your role is to decompose natural language instructions into structured subtasks
for a multi-arm robotic assembly system.

Key capabilities:
1. Understanding industrial assembly processes
2. Identifying dependencies between operations
3. Estimating task durations and resource requirements
4. Recognizing constraints and safety considerations

Output format: You must respond with valid JSON only, no additional text."""

    DECOMPOSE_TASK = """## Task Decomposition Request

**Instruction**: {instruction}

**Available Robot Arms**:
{robot_arms}

**Constraints**:
- Maximum {max_tasks} subtasks
- Each task must have clear dependencies
- Tasks must be executable by the available robot arms
- Consider safety and collision avoidance

**Required Output Format** (JSON):
```json
{{
    "objective": "Main goal of the instruction",
    "tasks": [
        {{
            "id": "task_001",
            "name": "Task Name",
            "description": "Detailed description of what this task does",
            "operation_type": "pick|place|move|assemble|inspect|tighten|weld|paint",
            "parameters": {{
                "object": "Target object",
                "source": "Source location",
                "destination": "Destination location",
                "precision": "high|medium|low"
            }},
            "dependencies": ["task_id_1", "task_id_2"],
            "estimated_duration": 2.5,
            "required_capabilities": ["gripper", "positioning"],
            "priority": 1
        }}
    ],
    "constraints": [
        "Constraint 1 description",
        "Constraint 2 description"
    ],
    "estimated_total_time": 15.0
}}
```

Please decompose the instruction into subtasks now."""

    VALIDATE_DECOMPOSITION = """## Task Decomposition Validation

**Original Instruction**: {instruction}

**Decomposed Tasks**:
{tasks}

Please validate this task decomposition:
1. Are all tasks necessary and sufficient to complete the instruction?
2. Are the dependencies correctly specified?
3. Are the estimated durations reasonable?
4. Are there any missing constraints or safety considerations?

**Required Output Format** (JSON):
```json
{{
    "is_valid": true|false,
    "issues": [
        {{
            "severity": "critical|warning|info",
            "description": "Issue description",
            "suggestion": "Suggested fix"
        }}
    ],
    "optimized_tasks": [/* Same format as input tasks if optimization needed */]
}}
```"""

    REFINE_TASK = """## Task Refinement Request

**Original Task**:
{task}

**Context**:
{context}

**Feedback**:
{feedback}

Please refine this task based on the feedback while maintaining consistency
with other tasks in the decomposition.

**Required Output Format** (JSON):
```json
{{
    "refined_task": {{
        /* Same format as original task */
    }},
    "changes_made": [
        "Description of change 1",
        "Description of change 2"
    ],
    "impact_on_other_tasks": [
        {{
            "task_id": "affected_task_id",
            "impact": "Description of impact"
        }}
    ]
}}
```"""

    @classmethod
    def get_decompose_prompt(
        cls,
        instruction: str,
        robot_arms: str,
        max_tasks: int = 20
    ) -> str:
        """
        Get the task decomposition prompt.

        Args:
            instruction: Natural language instruction to decompose.
            robot_arms: Description of available robot arms.
            max_tasks: Maximum number of subtasks allowed.

        Returns:
            Formatted prompt string.
        """
        return cls.DECOMPOSE_TASK.format(
            instruction=instruction,
            robot_arms=robot_arms,
            max_tasks=max_tasks
        )

    @classmethod
    def get_validation_prompt(
        cls,
        instruction: str,
        tasks: str
    ) -> str:
        """
        Get the task validation prompt.

        Args:
            instruction: Original instruction.
            tasks: JSON string of decomposed tasks.

        Returns:
            Formatted prompt string.
        """
        return cls.VALIDATE_DECOMPOSITION.format(
            instruction=instruction,
            tasks=tasks
        )

    @classmethod
    def get_refine_prompt(
        cls,
        task: str,
        context: str,
        feedback: str
    ) -> str:
        """
        Get the task refinement prompt.

        Args:
            task: Original task JSON.
            context: Context information.
            feedback: Feedback to incorporate.

        Returns:
            Formatted prompt string.
        """
        return cls.REFINE_TASK.format(
            task=task,
            context=context,
            feedback=feedback
        )
