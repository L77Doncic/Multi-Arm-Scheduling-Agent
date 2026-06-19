# Simulation

系统支持两种仿真后端，通过统一的 `SimulationInterface` 抽象接口切换。

## 仿真器对比

| 特性 | MockSimulator | IsaacSimInterface |
|------|--------------|-------------------|
| 环境要求 | **无特殊要求（CPU即可）** | NVIDIA GPU + Omniverse |
| 物理精度 | 软件模拟 | 物理引擎精确 |
| 执行速度 | 快（可加速） | 实时或略慢 |
| 用途 | 开发测试、CI/CD、**日常使用** | 最终验证、物理仿真 |
| 故障模拟 | 可配置概率 | 真实物理碰撞 |

!!! tip "GPU不是必需的"
    系统的核心功能（任务分解、资源分配、代码生成、闭环反馈）完全不依赖GPU。
    MockSimulator在CPU上运行，足以验证调度逻辑的正确性。
    仅在需要精确物理仿真（碰撞检测、力学模拟）时才需要Isaac Sim + GPU。

## MockSimulator

软件仿真器，无需GPU即可运行。模拟机械臂操作的时序和状态变化。

### 基本用法

```python
from simulation.mock_simulator import MockSimulator

sim = MockSimulator(
    failure_probabilities={"pick": 0.05, "assemble": 0.0},
    time_scale=100.0,  # 100倍速
    seed=42,            # 固定随机种子
)
sim.initialize()
sim.load_scene(scene_config)

# 执行动作
result = sim.execute_action("arm_001", {
    "type": "pick",
    "task_id": "t_001",
    "parameters": {"station_id": "s1"},
})

print(result.success)    # True
print(result.duration)   # 0.02 (加速后)
print(result.position)   # {'x': 0.0, 'y': 0.0, 'z': 0.5}

sim.close()
```

### 配置参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `failure_probabilities` | Dict[str, float] | 各操作5% | 每种操作类型的故障概率 |
| `action_durations` | Dict[str, float] | 预设值 | 每种操作的基准耗时（秒） |
| `time_scale` | float | 1.0 | 时间加速倍数 |
| `seed` | int | None | 随机种子（None=随机） |

### 默认操作耗时

```python
DEFAULT_DURATIONS = {
    "pick": 2.0,
    "place": 2.0,
    "move": 3.0,
    "assemble": 5.0,
    "inspect": 4.0,
    "tighten": 3.0,
    "weld": 6.0,
    "generic": 3.0,
}
```

### 执行追踪

MockSimulator 记录完整的执行轨迹：

```python
# 执行完毕后查看
for entry in sim._trace:
    print(f"{entry['arm_id']} | {entry['action']['type']} | "
          f"success={entry['result'].success} | t={entry['result'].duration}")
```

## IsaacSimInterface

NVIDIA Isaac Sim 接口。当 Isaac Sim 未安装时，自动降级到 MockSimulator。

```python
from simulation.isaac_sim import IsaacSimInterface

sim = IsaacSimInterface(config={
    "headless": True,
    "device": "cuda:0",
})
sim.initialize()  # 若Isaac不可用，自动使用MockSimulator
sim.load_scene(scene_config)

# 接口与MockSimulator完全一致
result = sim.execute_action("arm_001", action)

sim.close()
```

!!! tip
    即使在没有GPU的环境，`IsaacSimInterface` 也能正常工作——它会静默降级到 `MockSimulator`。

## SceneBuilder

场景构建器，从配置字典或参数创建场景。

### 从配置构建

```python
from simulation.scene_builder import SceneBuilder

builder = SceneBuilder()
scene = builder.build_from_config(scene_config)

print(scene.workstations)   # 工位列表
print(scene.workpieces)     # 工件列表
print(scene.robot_arms)     # 机械臂列表
```

### 参数化构建

```python
scene = builder.build_assembly_line(
    num_stations=4,
    num_workpieces=2,
    num_arms=3,
)
```

## 与SchedulingAgent集成

```python
from simulation.mock_simulator import MockSimulator

sim = MockSimulator(time_scale=100.0, seed=42)
sim.initialize()
sim.load_scene(scene_config)

result = agent.execute_scheduling(
    instruction=instruction,
    scene_config=scene_config,
    simulation=sim,  # 传入仿真器
)

# result.simulation_results 包含仿真详情
sim.close()
```
