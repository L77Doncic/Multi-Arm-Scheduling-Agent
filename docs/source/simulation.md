# Simulation

系统支持两种仿真后端，通过统一的 `SimulationInterface` 抽象接口切换。

## 仿真器对比

| 特性 | MockSimulator | IsaacSimInterface |
|------|--------------|-------------------|
| 环境要求 | CPU即可 | **NVIDIA RTX GPU (8GB+ VRAM)** |
| 物理精度 | 软件模拟（无物理引擎） | RTX渲染 + PhysX物理引擎 |
| 执行速度 | 快（可加速） | 实时或略慢 |
| 用途 | 开发调试、CI/CD | **最终仿真验证（必需）** |
| 故障模拟 | 可配置概率 | 真实物理碰撞检测 |

!!! warning "GPU是必需的"
    任务要求"接入Isaac Sim、Omniverse或Isaac Lab仿真接口完成执行验证"。
    Isaac Sim基于NVIDIA Omniverse平台，**必须使用RTX GPU**（最低RTX 3070, 8GB VRAM）。

    - ❌ GTX系列不支持（需要RTX的光线追踪核心）
    - ❌ 集成显卡/AMD显卡不支持
    - ✅ RTX 3070/3080/3090/4070/4080/4090 均可

    MockSimulator仅用于开发阶段的逻辑验证，**不能替代Isaac Sim的物理仿真**。

## MockSimulator

软件仿真器，无需GPU。用于开发阶段的调度逻辑验证，**不含物理引擎**。

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

NVIDIA Isaac Sim 接口。**需要NVIDIA RTX GPU和Omniverse环境。**

### 安装Isaac Sim

```bash
# 方式一：Omniverse Launcher（推荐）
# 从 https://developer.nvidia.com/isaac-sim 下载

# 方式二：pip安装
pip install isaacsim-kernel
pip install isaacsim-app
```

### 使用

```python
from simulation.isaac_sim import IsaacSimInterface

sim = IsaacSimInterface(config={
    "headless": True,      # 无头模式（不需要显示器）
    "device": "cuda:0",    # GPU设备
})
sim.initialize()           # 需要RTX GPU
sim.load_scene(scene_config)
result = sim.execute_action("arm_001", action)
sim.close()
```

!!! warning "Isaac Sim硬件要求"
    - GPU: NVIDIA RTX 3070+ (8GB+ VRAM)
    - Driver: NVIDIA 535+
    - RAM: 32GB+ (推荐64GB)
    - 存储: 50GB+ SSD

    若未安装Isaac Sim，`IsaacSimInterface` 会降级到 `MockSimulator`，但**不提供物理仿真验证**。

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
