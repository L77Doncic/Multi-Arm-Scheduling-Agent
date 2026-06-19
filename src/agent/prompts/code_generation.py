"""
Code Generation Prompt Templates

This module provides prompt templates for generating executable code
for robot arm tasks in multi-arm scheduling scenarios.
"""


class CodeGenerationPrompts:
    """Prompt templates for code generation."""

    SYSTEM_PROMPT = """You are an expert in robotics programming and code generation.
Your role is to generate executable Python code for robot arm tasks based on
task specifications and available capabilities.

Key requirements:
1. Code must be syntactically correct Python
2. Use provided atomic skill primitives
3. Include proper error handling
4. Add clear comments explaining each step
5. Follow safety guidelines
6. Support simulation execution

Output format: You must respond with valid JSON containing the generated code."""

    GENERATE_TASK_CODE = """## Code Generation Request

**Task Specification**:
{task_spec}

**Robot Arm Configuration**:
{arm_config}

**Available Skill Primitives**:
{skill_primitives}

**Safety Constraints**:
{safety_constraints}

**Code Requirements**:
1. Use only the provided skill primitives
2. Include proper error handling and validation
3. Add comments explaining each operation
4. Support both simulation and real execution
5. Respect workspace boundaries and payload limits

**Required Output Format** (JSON):
```json
{{
    "code": "import ...\\n\\ndef execute_task():\\n    ...",
    "language": "python",
    "dependencies": ["module1", "module2"],
    "parameters": {{
        "param1": {{"type": "float", "description": "Parameter description"}}
    }},
    "estimated_execution_time": 2.5,
    "safety_checks": [
        "Check 1 description",
        "Check 2 description"
    ],
    "test_cases": [
        {{
            "name": "Test case 1",
            "input": {{}},
            "expected_output": {{}}
        }}
    ]
}}
```

Please generate the code now."""

    GENERATE_SKILL_PRIMITIVE = """## Skill Primitive Generation

**Skill Name**: {skill_name}

**Skill Description**: {skill_description}

**Input Parameters**:
{input_parameters}

**Expected Behavior**:
{expected_behavior}

**Error Conditions**:
{error_conditions}

Please generate a reusable skill primitive function.

**Required Output Format** (JSON):
```json
{{
    "skill_code": "def skill_name(params):\\n    ...",
    "skill_name": "skill_name",
    "description": "Skill description",
    "parameters": [
        {{
            "name": "param1",
            "type": "float",
            "description": "Parameter description",
            "required": true,
            "default": null
        }}
    ],
    "return_type": "dict",
    "exceptions": [
        {{
            "name": "ExceptionName",
            "description": "When this exception occurs"
        }}
    ],
    "usage_example": "result = skill_name(param1=1.0)"
}}
```"""

    OPTIMIZE_CODE = """## Code Optimization Request

**Current Code**:
{current_code}

**Performance Metrics**:
{performance_metrics}

**Optimization Goals**:
{optimization_goals}

Please optimize this code while maintaining correctness.

**Required Output Format** (JSON):
```json
{{
    "optimized_code": "optimized code here",
    "optimizations_applied": [
        {{
            "type": "performance|readability|safety",
            "description": "What was optimized",
            "expected_improvement": "Expected improvement"
        }}
    ],
    "validation_required": true,
    "test_cases": [
        {{
            "name": "Test case",
            "input": {{}},
            "expected_output": {{}}
        }}
    ]
}}
```"""

    VALIDATE_CODE = """## Code Validation Request

**Code to Validate**:
{code}

**Task Specification**:
{task_spec}

**Validation Criteria**:
{validation_criteria}

Please validate this code against the task specification.

**Required Output Format** (JSON):
```json
{{
    "is_valid": true|false,
    "issues": [
        {{
            "severity": "error|warning|info",
            "line": 10,
            "description": "Issue description",
            "suggestion": "Suggested fix"
        }}
    ],
    "corrected_code": "corrected code if needed",
    "coverage": {{
        "requirements_met": 8,
        "requirements_total": 10,
        "missing_requirements": ["requirement 1", "requirement 2"]
    }}
}}
```"""

    @classmethod
    def get_code_generation_prompt(
        cls,
        task_spec: str,
        arm_config: str,
        skill_primitives: str,
        safety_constraints: str
    ) -> str:
        """
        Get the code generation prompt.

        Args:
            task_spec: Task specification JSON.
            arm_config: Robot arm configuration JSON.
            skill_primitives: Available skill primitives.
            safety_constraints: Safety constraints.

        Returns:
            Formatted prompt string.
        """
        return cls.GENERATE_TASK_CODE.format(
            task_spec=task_spec,
            arm_config=arm_config,
            skill_primitives=skill_primitives,
            safety_constraints=safety_constraints
        )

    @classmethod
    def get_skill_primitive_prompt(
        cls,
        skill_name: str,
        skill_description: str,
        input_parameters: str,
        expected_behavior: str,
        error_conditions: str
    ) -> str:
        """
        Get the skill primitive generation prompt.

        Args:
            skill_name: Name of the skill.
            skill_description: Description of the skill.
            input_parameters: Input parameters specification.
            expected_behavior: Expected behavior description.
            error_conditions: Error conditions to handle.

        Returns:
            Formatted prompt string.
        """
        return cls.GENERATE_SKILL_PRIMITIVE.format(
            skill_name=skill_name,
            skill_description=skill_description,
            input_parameters=input_parameters,
            expected_behavior=expected_behavior,
            error_conditions=error_conditions
        )

    @classmethod
    def get_optimization_prompt(
        cls,
        current_code: str,
        performance_metrics: str,
        optimization_goals: str
    ) -> str:
        """
        Get the code optimization prompt.

        Args:
            current_code: Current code to optimize.
            performance_metrics: Current performance metrics.
            optimization_goals: Optimization goals.

        Returns:
            Formatted prompt string.
        """
        return cls.OPTIMIZE_CODE.format(
            current_code=current_code,
            performance_metrics=performance_metrics,
            optimization_goals=optimization_goals
        )

    @classmethod
    def get_validation_prompt(
        cls,
        code: str,
        task_spec: str,
        validation_criteria: str
    ) -> str:
        """
        Get the code validation prompt.

        Args:
            code: Code to validate.
            task_spec: Task specification.
            validation_criteria: Validation criteria.

        Returns:
            Formatted prompt string.
        """
        return cls.VALIDATE_CODE.format(
            code=code,
            task_spec=task_spec,
            validation_criteria=validation_criteria
        )
