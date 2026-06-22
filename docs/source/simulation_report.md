# Simulation Report

## 测试环境

| 项目 | 值 |
|------|-----|
| 日期 | 2026-06-22 |
| OS | Linux 6.8.0-87-generic |
| Python | 3.12.3 |
| LLM | Xiaomi MiMo v2.5 (mimo-v2.5) |
| 仿真后端 | MockSimulator (time_scale=1.0x, seed=42) |

## 场景：4-Station Assembly Line

| 属性 | 值 |
|------|-----|
| 工位数 | 4 (Pick & Load → Assembly → Inspection → Packaging) |
| 工件数 | 2 (wp_A, wp_B) |
| 机械臂数 | 3 (Left Arm, Right Arm, Top Arm) |
| 任务数 | 8 |

### 执行结果

```
Execution ID:    5bdf620b
Tasks:           8
Success Rate:    100.0%
Violations:      0
```

### 任务分配

| 任务 | 操作 | 工件 | 分配臂 | 状态 |
|------|------|------|--------|------|
| t_001 | pick_workpiece_from_feed | wp_A | arm_003 (Top) | ✓ |
| t_002 | assemble_components | wp_A | arm_001 (Left) | ✓ |
| t_003 | quality_inspection | wp_A | arm_003 (Top) | ✓ |
| t_004 | package_and_output | wp_A | arm_001 (Left) | ✓ |
| t_005 | pick_workpiece_from_feed | wp_B | arm_001 (Left) | ✓ |
| t_006 | assemble_components | wp_B | arm_002 (Right) | ✓ |
| t_007 | quality_inspection | wp_B | arm_003 (Top) | ✓ |
| t_008 | package_and_output | wp_B | arm_002 (Right) | ✓ |

### 生成代码示例

**Pick 操作**（使用原语：move_to, linear_move, grip）：

```python
import time

def execute_pick_workpiece_from_feed_wp_A(arm_interface):
    results = {}
    start_time = time.time()

    arm_interface.move_to(0, 0, 0.65)
    arm_interface.linear_move(0, 0, -0.15, speed=0.5)
    arm_interface.grip(force=50.0)
    arm_interface.linear_move(0, 0, 0.1, speed=0.3)

    results['success'] = True
    results['picked'] = True
    results['duration'] = time.time() - start_time
    return results
```

**Assemble 操作**（使用原语：move_to, set_compliance, linear_move, check_sensor）：

```python
import time

def execute_assemble_components_wp_A(arm_interface):
    results = {}
    start_time = time.time()

    arm_interface.move_to(2.0, 0.0, 0.5)
    arm_interface.set_compliance(stiffness_x=200, stiffness_y=200, stiffness_z=100)
    arm_interface.linear_move(0, 0, -0.05, speed=0.1)
    sensor_data = arm_interface.check_sensor('force')
    assembly_ok = abs(sensor_data.get('fz', 0)) > 15.0

    results['assembly_force'] = sensor_data.get('fz', 0)
    results['success'] = assembly_ok
    results['duration'] = time.time() - start_time
    return results
```

### 原语使用统计

| 原语 | 使用次数 | 场景 |
|------|---------|------|
| move_to | 8 | 每个任务都需移动到目标位 |
| linear_move | 6 | 下降/提升/相对移动 |
| grip | 2 | 拾取工件 |
| release | 2 | 释放工件 |
| check_sensor | 4 | 力传感器验证装配、视觉检测 |
| set_compliance | 2 | 装配操作的柔顺控制 |

## 场景：MRTA-Benchmark

| Scenario | Arms | Workpieces | Stations | Tasks | Optimal |
|----------|------|------------|----------|-------|---------|
| Simple Pick-and-Place | 2 | 2 | 4 | 6 | 16.0s |
| Inspection Pipeline | 3 | 2 | 4 | 8 | 22.0s |
| Dual-Line Assembly | 3 | 4 | 4 | 12 | 20.0s |

所有场景均成功执行，100%任务完成率。

## 结论

1. 完整流水线（分解→分配→生成→执行→验证）运行正常
2. 基于能力匹配的资源分配策略有效利用多臂并行性
3. 动态代码生成正确组合了操作所需的原子原语
4. 异常重试机制确保了任务最终完成
5. 所有硬约束（时序、资源、空间）均未违反
