# Simulation

系统支持三种仿真后端，当前主要使用 Isaac Sim 4.5 进行物理仿真。

## 仿真后端

| 后端 | 环境要求 | 物理引擎 | 用途 |
|------|----------|----------|------|
| **IsaacSimInterface** | NVIDIA RTX GPU | PhysX | 物理级仿真验证（默认） |
| OmniverseInterface | NVIDIA RTX GPU | PhysX | 场景渲染 + 仿真 |
| IsaacLabInterface | NVIDIA RTX GPU | PhysX | RL训练 + 批量评估 |

## IsaacSimInterface（主要后端）

| 特性 | 说明 |
|------|------|
| 环境要求 | **NVIDIA RTX GPU (8GB+ VRAM)** |
| 物理精度 | PhysX物理引擎（重力、碰撞、关节） |
| 机械臂 | Franka Panda USD模型 |
| 控制方式 | Jacobian伪逆IK + 关节控制 |
| 旅行时间 | MRTA T_t矩阵（机械臂间移动时间） |
| 用途 | **物理仿真验证** |

!!! warning "GPU是必需的"
    Isaac Sim基于NVIDIA Omniverse平台，**必须使用RTX GPU**（最低RTX 3070, 8GB VRAM）。

    - ❌ GTX系列不支持（需要RTX的光线追踪核心）
    - ❌ 集成显卡/AMD显卡不支持
    - ✅ RTX 3070/3080/3090/4070/4080/4090/5090 均可

## IsaacSimInterface

### 安装Isaac Sim

```bash
# pip安装（推荐）
pip install isaacsim
pip install isaacsim-kernel
pip install isaacsim-app
```

### 使用

```python
from simulation.isaac_sim import IsaacSimInterface

sim = IsaacSimInterface(fallback_to_mock=False)
sim.initialize()
sim.load_scene(scene_config)

# 执行任务
result = agent.execute_scheduling(
    instruction=instruction,
    scene_config=scene_config,
    simulation=sim,
)

sim.close()
```

### 物理仿真程度

| 模块 | 实现方式 | 是否物理仿真 |
|------|----------|:------------:|
| 机械臂运动 | Jacobian IK | ✅ |
| 夹爪动作 | 物理步进 | ✅ |
| 抓取工件 | 传送+冻结 | ❌ |
| 释放工件 | 传送+重力 | ⚠️ |
| **旅行时间** | **MRTA T_t矩阵** | ✅ |

### MRTA旅行时间矩阵

系统实现了MRTA旅行时间矩阵（T_t），用于计算机械臂间的移动时间：

```python
# T_t矩阵定义了机械臂从位置i到位置j的旅行时间
# Makespan = max(task.end_time) - min(task.start_time)
# 其中task.end_time包含旅行时间
```

**效果**: Makespan与MRTA基准具有可比性，平均比率1.08x

### 视频录制

```python
# 帧捕获（需render=True）
frames = sim.get_frames()

# H.264编码
import subprocess
subprocess.run(["ffmpeg", "-i", "input.mp4", "-c:v", "libx264", "output.mp4"])
```

### 已知限制

1. 抓取工件通过"传送+冻结"实现，非物理绑定
2. FixedJoint在Isaac Sim pip包中API受限
3. `app.close()` 会导致进程崩溃，需子进程隔离
