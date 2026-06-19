"""
Resource Allocation Prompt Templates

This module provides prompt templates for allocating robot arms to tasks
in multi-arm scheduling scenarios.
"""


class ResourceAllocationPrompts:
    """Prompt templates for resource allocation."""

    SYSTEM_PROMPT = """You are an expert in multi-robot resource allocation and scheduling.
Your role is to optimally assign robot arms to tasks based on their capabilities,
current workload, and task requirements.

Key considerations:
1. Match task requirements with robot arm capabilities
2. Minimize total makespan (completion time)
3. Balance workload across robot arms
4. Avoid resource conflicts and collisions
5. Respect task dependencies and priorities

Output format: You must respond with valid JSON only, no additional text."""

    ALLOCATE_RESOURCES = """## Resource Allocation Request

**Tasks to Allocate**:
{tasks}

**Available Robot Arms**:
{robot_arms}

**Current State**:
{current_state}

**Optimization Objective**: {objective}

**Constraints**:
- Each task must be assigned to exactly one robot arm
- A robot arm can only execute one task at a time
- Task dependencies must be respected
- Robot arm capabilities must match task requirements

**Required Output Format** (JSON):
```json
{{
    "allocations": [
        {{
            "task_id": "task_001",
            "arm_id": "arm_001",
            "reason": "Explanation for this allocation",
            "confidence": 0.95
        }}
    ],
    "schedule": {{
        "arm_001": [
            {{"task_id": "task_001", "start_time": 0.0, "end_time": 2.5}},
            {{"task_id": "task_003", "start_time": 2.5, "end_time": 5.0}}
        ],
        "arm_002": [
            {{"task_id": "task_002", "start_time": 0.0, "end_time": 3.0}}
        ]
    }},
    "estimated_makespan": 5.0,
    "resource_utilization": {{
        "arm_001": 0.85,
        "arm_002": 0.72
    }},
    "warnings": [
        "Any warnings or potential issues"
    ]
}}
```

Please allocate resources now."""

    RESOLVE_CONFLICT = """## Conflict Resolution Request

**Conflict Description**:
{conflict}

**Current Allocations**:
{current_allocations}

**Available Options**:
{options}

Please resolve this conflict while minimizing impact on overall schedule.

**Required Output Format** (JSON):
```json
{{
    "resolution": {{
        "strategy": "reassign|delay|parallel|cancel",
        "description": "Explanation of resolution"
    }},
    "updated_allocations": [
        /* Same format as original allocations */
    ],
    "impact": {{
        "makespan_change": 0.5,
        "affected_tasks": ["task_001", "task_002"]
    }}
}}
```"""

    OPTIMIZE_SCHEDULE = """## Schedule Optimization Request

**Current Schedule**:
{current_schedule}

**Performance Metrics**:
{metrics}

**Optimization Goals**:
{goals}

Please suggest optimizations to improve the schedule performance.

**Required Output Format** (JSON):
```json
{{
    "optimizations": [
        {{
            "type": "reorder|reassign|parallelize|batch",
            "description": "What to optimize",
            "expected_improvement": "Expected improvement description",
            "changes": [
                {{
                    "task_id": "task_001",
                    "original": {{/* Original allocation */}},
                    "optimized": {{/* Optimized allocation */}}
                }}
            ]
        }}
    ],
    "estimated_improvement": {{
        "makespan_reduction": 1.5,
        "utilization_increase": 0.1
    }}
}}
```"""

    @classmethod
    def get_allocation_prompt(
        cls,
        tasks: str,
        robot_arms: str,
        current_state: str,
        objective: str = "minimize_makespan"
    ) -> str:
        """
        Get the resource allocation prompt.

        Args:
            tasks: JSON string of tasks to allocate.
            robot_arms: JSON string of available robot arms.
            current_state: JSON string of current system state.
            objective: Optimization objective.

        Returns:
            Formatted prompt string.
        """
        return cls.ALLOCATE_RESOURCES.format(
            tasks=tasks,
            robot_arms=robot_arms,
            current_state=current_state,
            objective=objective
        )

    @classmethod
    def get_conflict_resolution_prompt(
        cls,
        conflict: str,
        current_allocations: str,
        options: str
    ) -> str:
        """
        Get the conflict resolution prompt.

        Args:
            conflict: Description of the conflict.
            current_allocations: Current resource allocations.
            options: Available resolution options.

        Returns:
            Formatted prompt string.
        """
        return cls.RESOLVE_CONFLICT.format(
            conflict=conflict,
            current_allocations=current_allocations,
            options=options
        )

    @classmethod
    def get_optimization_prompt(
        cls,
        current_schedule: str,
        metrics: str,
        goals: str
    ) -> str:
        """
        Get the schedule optimization prompt.

        Args:
            current_schedule: Current schedule JSON.
            metrics: Current performance metrics.
            goals: Optimization goals.

        Returns:
            Formatted prompt string.
        """
        return cls.OPTIMIZE_SCHEDULE.format(
            current_schedule=current_schedule,
            metrics=metrics,
            goals=goals
        )
