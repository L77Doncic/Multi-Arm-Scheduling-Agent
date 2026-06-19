# Task Decomposition

任务分解是调度流程的第一步：将自然语言指令转化为结构化的任务依赖图。

## 工作原理

系统支持两种分解模式：

| 模式 | 触发条件 | 方法 |
|------|---------|------|
| **LLM模式** | 配置了 `llm.provider` | 使用结构化提示词让LLM输出JSON任务计划 |
| **启发式模式** | 未配置LLM或LLM失败 | 基于关键词匹配 + 场景配置解析 |

两种模式输出相同的 `TaskPlan` 数据结构，对下游模块透明。

## 输入

### 自然语言指令

```python
instruction = """
Two workpieces (A and B) need to be assembled on a 4-station line.
Each workpiece must be picked, assembled, inspected, and packaged.
Three robot arms are available. Minimize total completion time.
"""
```

### 场景配置（可选但推荐）

```python
scene = {
    "stations": [
        {
            "id": "station_1",
            "name": "Pick & Load",
            "operation": "pick_workpiece_from_feed",
            "capabilities_required": ["pick", "place"],
            "estimated_duration": 3.0,
            "predecessors": [],
            "successors": ["station_2"],
        },
        {
            "id": "station_2",
            "name": "Assembly",
            "operation": "assemble_components",
            "capabilities_required": ["assemble", "gripper", "force_control"],
            "estimated_duration": 8.0,
            "predecessors": ["station_1"],
            "successors": ["station_3"],
        },
        # ...
    ],
    "workpieces": [
        {
            "id": "wp_A",
            "operations_sequence": ["station_1", "station_2", "station_3", "station_4"],
            "priority": 1,
        },
    ],
}
```

## 输出：TaskPlan

```python
plan = planner.create_plan(instruction, scene)

# plan.tasks → List[TaskNode]
# plan.dependency_graph → Dict[str, List[str]]
# plan.estimated_makespan → float
# plan.get_execution_order() → List[List[str]]  # 拓扑排序层级
```

### 执行顺序（拓扑排序）

```
Level 0 (并行):  t_001 (pick A),  t_005 (pick B)
Level 1 (并行):  t_002 (assemble A),  t_006 (assemble B)
Level 2 (串行):  t_003 (inspect A),  t_007 (inspect B)  ← 共享质检工位
Level 3 (并行):  t_004 (package A),  t_008 (package B)
```

## 启发式分解详解

当无LLM时，系统使用以下规则：

### 1. 操作识别

基于关键词匹配识别操作类型：

```python
patterns = {
    "pick":     ["pick", "grab", "grasp", "take", "lift"],
    "place":    ["place", "put", "position", "set", "drop"],
    "assemble": ["assemble", "connect", "attach", "join", "fasten"],
    "inspect":  ["inspect", "check", "verify", "examine"],
    "tighten":  ["tighten", "secure", "bolt", "screw"],
    "weld":     ["weld", "solder", "bond"],
    # ...
}
```

### 2. 依赖推断

- 有场景配置时：按 `operations_sequence` 顺序建立依赖
- 无配置时：按指令中操作出现的顺序建立串行依赖

### 3. 能力映射

```python
capability_map = {
    "pick":     ["gripper", "positioning"],
    "assemble": ["gripper", "positioning", "force_control"],
    "inspect":  ["vision", "positioning"],
    "tighten":  ["gripper", "force_control", "torque_control"],
    # ...
}
```

## LLM模式

当配置了LLM时，系统使用结构化提示词：

```python
prompt = f"""
Given the following instruction and scene configuration, decompose
the task into a structured list of subtasks.

Instruction: {instruction}
Scene: {json.dumps(scene)}

Output a JSON object with:
- tasks: array of task objects, each with:
  - id, name, description, operation_type
  - required_capabilities (array of strings)
  - estimated_duration (float, seconds)
  - dependencies (array of task IDs)
  - station_id, workpiece_id

Ensure the dependency graph is a DAG (no cycles).
"""
```

LLM返回的JSON被解析为 `TaskPlan`。如果解析失败，自动回退到启发式模式。

## 使用示例

```python
from agent.planner import TaskPlanner

planner = TaskPlanner(config={}, llm_client=None)  # 启发式模式

# 从场景配置分解
plan = planner.create_plan(
    instruction="Assemble two workpieces",
    scene_config=scene,
)

# 查看结果
for task in plan.tasks:
    print(f"{task.id}: {task.name} (deps={task.dependencies})")

print(f"Estimated makespan: {plan.estimated_makespan}s")
print(f"Execution levels: {plan.get_execution_order()}")
```
