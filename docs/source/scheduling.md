# Scheduling

资源分配模块将分解后的任务分配给最合适的机械臂。

## 分配策略

分配采用**贪心算法**，综合考虑三个因素：

```
score = capability_weight × cap_score + workload_weight × balance_score + priority_weight × priority_score
```

默认权重：`capability=0.6, workload=0.3, priority=0.1`

| 因素 | 权重 | 说明 |
|------|------|------|
| 能力匹配 | 60% | 机械臂能力覆盖任务需求的比例 |
| 负载均衡 | 30% | 优先分配给当前负载较低的臂 |
| 任务优先级 | 10% | 高优先级任务优先分配 |

### 能力匹配

```python
# 任务需要: ["assemble", "gripper", "force_control"]
# 机械臂拥有: ["pick", "place", "assemble", "gripper", "force_control"]

caps_match = len(required ∩ available)  # = 3
caps_needed = len(required)             # = 3
cap_score = caps_match / caps_needed    # = 1.0
```

如果能力覆盖率 < 50%，该臂不参与分配。

### 负载均衡

```python
load_score = 1.0 / (1.0 + arm_total_busy_time)
```

忙碌时间越短的臂，得分越高。

## 分配流程

```
1. 按依赖层级排序任务（独立任务优先）
2. 对每个任务:
   a. 计算每个臂的综合得分
   b. 分配给得分最高的臂
   c. 更新该臂的负载
3. 检测并解决冲突
```

## 冲突检测

系统检测以下类型的冲突：

| 冲突类型 | 说明 | 检测方式 |
|----------|------|---------|
| 时序冲突 | 同一臂在同一时间段执行多个任务 | 时间区间重叠检测 |
| 资源冲突 | 同一臂同时被分配给互斥任务 | 依赖关系分析 |
| 空间冲突 | 机械臂工作空间重叠 | 位置 + 臂展半径 |

## 使用示例

```python
from agent.core import SchedulingAgent

agent = SchedulingAgent(config)

# 执行完整调度流水线
result = agent.execute_scheduling(
    instruction=instruction,
    scene_config=scene_config,
)

# 查看分配结果
for task_id, arm_id in result.allocation.items():
    arm = agent.robot_arms[arm_id]
    print(f"{task_id} → {arm.name} ({arm_id})")
```

输出：

```
t_001 → Top Arm (arm_003)
t_002 → Left Arm (arm_001)
t_003 → Top Arm (arm_003)
t_004 → Left Arm (arm_001)
t_005 → Left Arm (arm_001)
t_006 → Right Arm (arm_002)
t_007 → Top Arm (arm_003)
t_008 → Right Arm (arm_002)
```

## ResourceAllocator API

如果需要更精细的控制，可以直接使用 `ResourceAllocator`：

```python
from harness.resource_allocator import ResourceAllocator

allocator = ResourceAllocator(config={})

task_dicts = [
    {"id": "t1", "required_capabilities": ["pick"], "estimated_duration": 2.0, ...},
    {"id": "t2", "required_capabilities": ["assemble"], "estimated_duration": 5.0, ...},
]
arm_dicts = [
    {"id": "arm1", "capabilities": ["pick", "place", "assemble"]},
    {"id": "arm2", "capabilities": ["pick", "inspect"]},
]

allocation = allocator.allocate(task_dicts, arm_dicts)
# → {"t1": "arm1", "t2": "arm1"}
# allocate() 内部自动检测并解决冲突
```
