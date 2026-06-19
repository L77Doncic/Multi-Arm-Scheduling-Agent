"""
Code Generator Module

Generates executable Python code for robot arm tasks using atomic primitives.
The generated code is task-specific and dynamically composed based on
operation requirements - NOT pulled from a pre-built skill library.
"""

import json
import logging
import textwrap
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# Atomic skill primitives that generated code can call
ATOMIC_PRIMITIVES = {
    'move_to': {
        'params': ['x', 'y', 'z', 'speed'],
        'description': 'Move end-effector to absolute position',
        'return': 'bool (success)',
    },
    'grip': {
        'params': ['force'],
        'description': 'Close gripper with specified force',
        'return': 'bool (success)',
    },
    'release': {
        'params': [],
        'description': 'Open gripper to release object',
        'return': 'bool (success)',
    },
    'rotate': {
        'params': ['roll', 'pitch', 'yaw', 'speed'],
        'description': 'Rotate end-effector to orientation',
        'return': 'bool (success)',
    },
    'linear_move': {
        'params': ['dx', 'dy', 'dz', 'speed'],
        'description': 'Move relative to current position',
        'return': 'bool (success)',
    },
    'wait': {
        'params': ['duration'],
        'description': 'Wait for specified duration (seconds)',
        'return': 'bool',
    },
    'check_sensor': {
        'params': ['sensor_type'],
        'description': 'Read sensor value (force, vision, proximity)',
        'return': 'dict (sensor_data)',
    },
    'set_payload': {
        'params': ['mass'],
        'description': 'Declare current payload mass for dynamics',
        'return': 'bool',
    },
    'set_compliance': {
        'params': ['stiffness_x', 'stiffness_y', 'stiffness_z'],
        'description': 'Set Cartesian stiffness for contact tasks',
        'return': 'bool',
    },
}


@dataclass
class GeneratedCode:
    """Container for generated executable code."""
    task_id: str
    arm_id: str
    code: str
    imports: List[str]
    primitives_used: List[str]
    estimated_duration: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class CodeGenerator:
    """
    Generates executable Python code for robot arm tasks.

    The generator composes code from atomic primitives based on the specific
    task requirements. Each generated function is unique to the task context,
    not a lookup from a fixed skill library.
    """

    def __init__(self, config: Dict[str, Any], llm_client=None):
        self.config = config
        self.llm_client = llm_client
        self.generation_counter = 0
        logger.info("CodeGenerator initialized")

    def generate(self, task_name: str, task_description: str,
                 operation_type: str, arm_id: str,
                 required_capabilities: List[str],
                 parameters: Optional[Dict] = None,
                 feedback: Optional[Dict] = None) -> GeneratedCode:
        """
        Generate executable code for a specific task on a specific arm.

        Args:
            task_name: Name/ID of the task.
            task_description: Natural language description of what to do.
            operation_type: Type of operation (pick, place, assemble, etc.).
            arm_id: ID of the robot arm.
            required_capabilities: Capabilities needed.
            parameters: Task-specific parameters (positions, forces, etc.).
            feedback: Optional feedback from previous execution for refinement.

        Returns:
            GeneratedCode with the executable Python code.
        """
        self.generation_counter += 1
        logger.info("Generating code for %s on %s (op=%s)",
                     task_name, arm_id, operation_type)

        if self.llm_client and not feedback:
            code = self._generate_with_llm(
                task_name, task_description, operation_type,
                arm_id, required_capabilities, parameters
            )
        elif self.llm_client and feedback:
            code = self._refine_with_llm(
                task_name, task_description, operation_type,
                arm_id, required_capabilities, parameters, feedback
            )
        else:
            code = self._generate_with_template(
                task_name, task_description, operation_type,
                arm_id, required_capabilities, parameters
            )

        logger.info("Generated code for %s using primitives: %s",
                     task_name, code.primitives_used)
        return code

    def _generate_with_template(self, task_name: str, task_description: str,
                                 operation_type: str, arm_id: str,
                                 capabilities: List[str],
                                 parameters: Optional[Dict]) -> GeneratedCode:
        """Generate code using template-based composition."""
        params = parameters or {}
        primitives_used: List[str] = []
        code_lines: List[str] = []

        # Generate function signature
        func_name = f"execute_{task_name.replace(' ', '_').lower()}"
        code_lines.append(f"def {func_name}(arm_interface):")
        code_lines.append(f'    """')
        code_lines.append(f"    {task_description}")
        code_lines.append(f'    Arm: {arm_id}')
        code_lines.append(f'    Operation: {operation_type}')
        code_lines.append(f'    """')
        code_lines.append(f"    results = {{}}")
        code_lines.append(f"    start_time = time.time()")
        code_lines.append(f"")

        # Compose operation-specific code from primitives
        op_lines: List[str] = []
        if operation_type in ('pick', 'pick_workpiece_from_feed', 'pick_from_feed'):
            op_lines, prims = self._compose_pick_code(params)
            primitives_used.extend(prims)

        elif operation_type in ('place', 'package', 'package_and_output',
                                 'output', 'drop'):
            op_lines, prims = self._compose_place_code(params)
            primitives_used.extend(prims)

        elif operation_type in ('move', 'transfer', 'transport'):
            op_lines, prims = self._compose_move_code(params)
            primitives_used.extend(prims)

        elif operation_type in ('assemble', 'assemble_components',
                                 'final_assembly', 'join', 'connect'):
            op_lines, prims = self._compose_assemble_code(params)
            primitives_used.extend(prims)

        elif operation_type in ('inspect', 'quality_inspection',
                                 'quality_check', 'verify'):
            op_lines, prims = self._compose_inspect_code(params)
            primitives_used.extend(prims)

        elif operation_type in ('tighten', 'secure', 'bolt'):
            op_lines, prims = self._compose_tighten_code(params)
            primitives_used.extend(prims)

        elif operation_type in ('weld', 'weld_joints', 'solder'):
            op_lines, prims = self._compose_weld_code(params)
            primitives_used.extend(prims)

        elif operation_type in ('prepare', 'prepare_workpiece', 'prep'):
            op_lines, prims = self._compose_prep_code(params)
            primitives_used.extend(prims)

        else:
            # Generic operation
            op_lines, prims = self._compose_generic_code(operation_type, params)
            primitives_used.extend(prims)

        code_lines.extend(op_lines)

        # Add result collection and return
        code_lines.append(f"    elapsed = time.time() - start_time")
        code_lines.append(f"    results['duration'] = elapsed")
        code_lines.append(f"    results['status'] = 'completed'")
        code_lines.append(f"    return results")

        code_body = "\n".join(code_lines)

        # Full module code with imports
        imports = ["import time"]
        if 'check_sensor' in primitives_used:
            imports.append("import numpy as np")

        full_code = "\n".join(imports) + "\n\n\n" + code_body

        return GeneratedCode(
            task_id=task_name,
            arm_id=arm_id,
            code=full_code,
            imports=imports,
            primitives_used=list(set(primitives_used)),
            estimated_duration=params.get('estimated_duration', 3.0),
            metadata={'method': 'template', 'operation_type': operation_type}
        )

    def _compose_pick_code(self, params: Dict) -> tuple:
        """Compose code for pick operations."""
        lines = []
        prims = []

        target = params.get('target_position', {'x': 0, 'y': 0, 'z': 0.5})
        approach_z = target.get('z', 0.5) + 0.15
        force = params.get('grip_force', 50.0)

        lines.append(f"    # Approach position above target")
        lines.append(f"    arm_interface.move_to({target['x']}, {target['y']}, {approach_z})")
        prims.append('move_to')

        lines.append(f"    # Descend to target")
        lines.append(f"    arm_interface.linear_move(0, 0, {target['z'] - approach_z}, speed=0.5)")
        prims.append('linear_move')

        lines.append(f"    # Grip object")
        lines.append(f"    arm_interface.grip(force={force})")
        prims.append('grip')

        lines.append(f"    # Lift object")
        lines.append(f"    arm_interface.linear_move(0, 0, 0.1, speed=0.3)")
        prims.append('linear_move')

        lines.append(f"    results['success'] = True")
        lines.append(f"    results['picked'] = True")

        return lines, prims

    def _compose_place_code(self, params: Dict) -> tuple:
        """Compose code for place operations."""
        lines = []
        prims = []

        target = params.get('target_position', {'x': 0, 'y': 0, 'z': 0.3})

        lines.append(f"    # Move to place position")
        lines.append(f"    arm_interface.move_to({target['x']}, {target['y']}, {target['z'] + 0.1})")
        prims.append('move_to')

        lines.append(f"    # Lower to surface")
        lines.append(f"    arm_interface.linear_move(0, 0, -0.1, speed=0.3)")
        prims.append('linear_move')

        lines.append(f"    # Release object")
        lines.append(f"    arm_interface.release()")
        prims.append('release')

        lines.append(f"    # Retract")
        lines.append(f"    arm_interface.linear_move(0, 0, 0.15, speed=0.5)")
        prims.append('linear_move')

        lines.append(f"    results['success'] = True")
        lines.append(f"    results['placed'] = True")

        return lines, prims

    def _compose_move_code(self, params: Dict) -> tuple:
        """Compose code for move/transport operations."""
        lines = []
        prims = []

        source = params.get('source_position', {'x': 0, 'y': 0, 'z': 0.5})
        dest = params.get('target_position', {'x': 2, 'y': 0, 'z': 0.5})
        speed = params.get('speed', 1.0)

        lines.append(f"    # Move to destination")
        lines.append(f"    arm_interface.move_to({dest['x']}, {dest['y']}, {dest['z']}, speed={speed})")
        prims.append('move_to')

        lines.append(f"    results['success'] = True")
        lines.append(f"    results['moved_to'] = ({dest['x']}, {dest['y']}, {dest['z']})")

        return lines, prims

    def _compose_assemble_code(self, params: Dict) -> tuple:
        """Compose code for assembly operations."""
        lines = []
        prims = []

        target = params.get('assembly_position', {'x': 2, 'y': 0, 'z': 0.5})
        force = params.get('assembly_force', 30.0)

        lines.append(f"    # Move to assembly position")
        lines.append(f"    arm_interface.move_to({target['x']}, {target['y']}, {target['z']})")
        prims.append('move_to')

        lines.append(f"    # Set compliance for contact")
        lines.append(f"    arm_interface.set_compliance(stiffness_x=200, stiffness_y=200, stiffness_z=100)")
        prims.append('set_compliance')

        lines.append(f"    # Apply assembly force via slow descent")
        lines.append(f"    arm_interface.linear_move(0, 0, -0.05, speed=0.1)")
        prims.append('linear_move')

        lines.append(f"    # Verify assembly with force sensor")
        lines.append(f"    sensor_data = arm_interface.check_sensor('force')")
        prims.append('check_sensor')

        lines.append(f"    assembly_ok = abs(sensor_data.get('fz', 0)) > {force * 0.5}")
        lines.append(f"    results['assembly_force'] = sensor_data.get('fz', 0)")
        lines.append(f"    results['success'] = assembly_ok")

        return lines, prims

    def _compose_inspect_code(self, params: Dict) -> tuple:
        """Compose code for inspection operations."""
        lines = []
        prims = []

        target = params.get('inspection_position', {'x': 4, 'y': 0, 'z': 0.5})

        lines.append(f"    # Move to inspection position")
        lines.append(f"    arm_interface.move_to({target['x']}, {target['y']}, {target['z']})")
        prims.append('move_to')

        lines.append(f"    # Capture vision data")
        lines.append(f"    vision_data = arm_interface.check_sensor('vision')")
        prims.append('check_sensor')

        lines.append(f"    # Analyze inspection result")
        lines.append(f"    defect_score = vision_data.get('defect_score', 0.0)")
        lines.append(f"    passed = defect_score < 0.1")
        lines.append(f"    results['defect_score'] = defect_score")
        lines.append(f"    results['passed'] = passed")
        lines.append(f"    results['success'] = True")

        return lines, prims

    def _compose_tighten_code(self, params: Dict) -> tuple:
        """Compose code for tightening operations."""
        lines = []
        prims = []

        target = params.get('fastener_position', {'x': 2, 'y': 0, 'z': 0.5})
        torque = params.get('target_torque', 5.0)

        lines.append(f"    # Move to fastener position")
        lines.append(f"    arm_interface.move_to({target['x']}, {target['y']}, {target['z']})")
        prims.append('move_to')

        lines.append(f"    # Rotate to tighten")
        lines.append(f"    arm_interface.rotate(roll=0, pitch=0, yaw=360, speed=0.5)")
        prims.append('rotate')

        lines.append(f"    # Verify torque")
        lines.append(f"    torque_data = arm_interface.check_sensor('force')")
        prims.append('check_sensor')

        lines.append(f"    results['applied_torque'] = torque_data.get('tz', 0)")
        lines.append(f"    results['success'] = abs(torque_data.get('tz', 0)) >= {torque * 0.8}")

        return lines, prims

    def _compose_weld_code(self, params: Dict) -> tuple:
        """Compose code for welding operations."""
        lines = []
        prims = []

        start = params.get('weld_start', {'x': 2, 'y': -0.5, 'z': 0.5})
        end = params.get('weld_end', {'x': 2, 'y': 0.5, 'z': 0.5})

        lines.append(f"    # Move to weld start position")
        lines.append(f"    arm_interface.move_to({start['x']}, {start['y']}, {start['z']})")
        prims.append('move_to')

        lines.append(f"    # Enable welding tool")
        lines.append(f"    arm_interface.check_sensor('weld_trigger')")
        prims.append('check_sensor')

        lines.append(f"    # Linear weld pass")
        lines.append(f"    arm_interface.linear_move(0, {end['y'] - start['y']}, 0, speed=0.2)")
        prims.append('linear_move')

        lines.append(f"    # Verify weld quality")
        lines.append(f"    weld_data = arm_interface.check_sensor('vision')")
        prims.append('check_sensor')

        lines.append(f"    results['weld_length'] = abs({end['y'] - start['y']})")
        lines.append(f"    results['quality'] = weld_data.get('weld_quality', 0.9)")
        lines.append(f"    results['success'] = results['quality'] > 0.8")

        return lines, prims

    def _compose_prep_code(self, params: Dict) -> tuple:
        """Compose code for preparation operations."""
        lines = []
        prims = []

        target = params.get('prep_position', {'x': 2, 'y': 0, 'z': 0.5})

        lines.append(f"    # Move to preparation station")
        lines.append(f"    arm_interface.move_to({target['x']}, {target['y']}, {target['z']})")
        prims.append('move_to')

        lines.append(f"    # Orient workpiece for processing")
        lines.append(f"    arm_interface.rotate(roll=0, pitch=90, yaw=0, speed=0.5)")
        prims.append('rotate')

        lines.append(f"    # Check alignment")
        lines.append(f"    align_data = arm_interface.check_sensor('vision')")
        prims.append('check_sensor')

        lines.append(f"    results['aligned'] = align_data.get('alignment_ok', True)")
        lines.append(f"    results['success'] = True")

        return lines, prims

    def _compose_generic_code(self, operation_type: str, params: Dict) -> tuple:
        """Compose code for generic/unknown operations."""
        lines = []
        prims = []

        lines.append(f"    # Generic operation: {operation_type}")
        lines.append(f"    # Check environment")
        lines.append(f"    env_data = arm_interface.check_sensor('proximity')")
        prims.append('check_sensor')

        lines.append(f"    # Execute operation")
        lines.append(f"    arm_interface.wait(duration=1.0)")
        prims.append('wait')

        lines.append(f"    results['operation'] = '{operation_type}'")
        lines.append(f"    results['success'] = True")

        return lines, prims

    def _generate_with_llm(self, task_name: str, task_description: str,
                            operation_type: str, arm_id: str,
                            capabilities: List[str],
                            parameters: Optional[Dict]) -> GeneratedCode:
        """Use LLM to generate code for a task."""
        from .prompts.code_generation import code_generate_prompt

        prompt = code_generate_prompt(
            task_name=task_name,
            task_description=task_description,
            operation_type=operation_type,
            arm_id=arm_id,
            capabilities=capabilities,
            parameters=parameters or {},
            available_primitives=list(ATOMIC_PRIMITIVES.keys())
        )

        try:
            response = self.llm_client.generate(prompt)
            # Extract code from response
            code_text = self._extract_code_from_response(response)
            primitives = self._detect_primitives_used(code_text)

            return GeneratedCode(
                task_id=task_name,
                arm_id=arm_id,
                code=code_text,
                imports=["import time", "import numpy as np"],
                primitives_used=primitives,
                estimated_duration=(parameters or {}).get('estimated_duration', 3.0),
                metadata={'method': 'llm', 'operation_type': operation_type}
            )
        except Exception as e:
            logger.warning("LLM code generation failed (%s), using template", e)
            return self._generate_with_template(
                task_name, task_description, operation_type,
                arm_id, capabilities, parameters
            )

    def _refine_with_llm(self, task_name: str, task_description: str,
                          operation_type: str, arm_id: str,
                          capabilities: List[str],
                          parameters: Optional[Dict],
                          feedback: Dict) -> GeneratedCode:
        """Refine previously generated code based on execution feedback."""
        from .prompts.code_generation import code_refine_prompt

        prompt = code_refine_prompt(
            task_name=task_name,
            original_code=feedback.get('original_code', ''),
            execution_result=feedback.get('execution_result', {}),
            error_message=feedback.get('error', ''),
            available_primitives=list(ATOMIC_PRIMITIVES.keys())
        )

        try:
            response = self.llm_client.generate(prompt)
            code_text = self._extract_code_from_response(response)
            primitives = self._detect_primitives_used(code_text)

            return GeneratedCode(
                task_id=task_name,
                arm_id=arm_id,
                code=code_text,
                imports=["import time", "import numpy as np"],
                primitives_used=primitives,
                estimated_duration=(parameters or {}).get('estimated_duration', 3.0),
                metadata={'method': 'llm_refined', 'operation_type': operation_type}
            )
        except Exception as e:
            logger.warning("LLM code refinement failed (%s), using template", e)
            return self._generate_with_template(
                task_name, task_description, operation_type,
                arm_id, capabilities, parameters
            )

    def _extract_code_from_response(self, response: str) -> str:
        """Extract Python code from LLM response."""
        # Look for code blocks
        if "```python" in response:
            start = response.index("```python") + len("```python")
            end = response.index("```", start)
            return response[start:end].strip()
        elif "```" in response:
            start = response.index("```") + 3
            end = response.index("```", start)
            return response[start:end].strip()
        return response.strip()

    def _detect_primitives_used(self, code: str) -> List[str]:
        """Detect which atomic primitives are used in the code."""
        primitives = []
        for prim in ATOMIC_PRIMITIVES:
            if f"arm_interface.{prim}(" in code:
                primitives.append(prim)
        return primitives
