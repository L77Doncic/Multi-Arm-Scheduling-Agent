# Code Generation

代码生成模块为每个任务动态生成可执行的Python代码。

## 设计原则

!!! warning "核心约束"
    系统**禁止使用预置的完整固定技能库**。每次代码生成都是基于任务具体参数，从原子原语实时组合。

这意味着：
- 同一个 `pick` 操作，拾取不同位置的工件会生成**不同的代码**
- 同一个 `assemble` 操作，不同力控参数会生成**不同的代码**
- 代码质量可以通过反馈闭环**持续改进**

## 原子原语

代码生成器使用以下9种原语作为构建块：

```python
# 位置控制
arm_interface.move_to(x, y, z, speed)       # 绝对位置移动
arm_interface.linear_move(dx, dy, dz, speed) # 相对位移
arm_interface.rotate(roll, pitch, yaw, speed) # 旋转

# 末端执行器
arm_interface.grip(force)    # 闭合夹爪
arm_interface.release()      # 释放工件

# 传感器
arm_interface.check_sensor(sensor_type)  # 'force' / 'vision' / 'proximity'

# 参数设置
arm_interface.set_payload(mass)                    # 声明负载
arm_interface.set_compliance(stiffness_x, stiffness_y, stiffness_z)  # 柔顺控制

# 时序
arm_interface.wait(duration)  # 等待
```

## 代码生成流程

```
Task(operation_type="pick", station_id="s1", workpiece_id="wp_A")
    │
    ▼
CodeGenerator.generate()
    │
    ├── LLM模式: 提示词 → LLM生成代码 → 提取Python代码
    │
    └── 模板模式: 选择操作模板 → 填充参数 → 组合原语
    │
    ▼
GeneratedCode(
    code="import time\n\ndef execute_pick_wp_A(arm_interface):\n    ...",
    primitives_used=["move_to", "grip", "linear_move"],
    estimated_duration=2.0,
)
```

## 模板模式详解

每种操作类型有对应的原语组合模式：

### Pick 操作

```python
def execute_pick_wp_A(arm_interface):
    """Pick workpiece A from feed station."""
    results = {}
    start_time = time.time()

    # 1. 移动到目标上方
    arm_interface.move_to(0.0, 0.0, 0.65)

    # 2. 下降到目标
    arm_interface.linear_move(0, 0, -0.15, speed=0.5)

    # 3. 夹取
    arm_interface.grip(force=50.0)

    # 4. 提升
    arm_interface.linear_move(0, 0, 0.1, speed=0.3)

    results['success'] = True
    results['picked'] = True
    results['duration'] = time.time() - start_time
    return results
```

### Assemble 操作

```python
def execute_assemble_wp_A(arm_interface):
    """Assemble workpiece A at assembly station."""
    results = {}
    start_time = time.time()

    # 1. 移动到装配位
    arm_interface.move_to(2.0, 0.0, 0.5)

    # 2. 设置柔顺控制（接触任务必须）
    arm_interface.set_compliance(stiffness_x=200, stiffness_y=200, stiffness_z=100)

    # 3. 慢速下降施加装配力
    arm_interface.linear_move(0, 0, -0.05, speed=0.1)

    # 4. 力传感器验证装配
    sensor_data = arm_interface.check_sensor('force')
    assembly_ok = abs(sensor_data.get('fz', 0)) > 15.0

    results['assembly_force'] = sensor_data.get('fz', 0)
    results['success'] = assembly_ok
    results['duration'] = time.time() - start_time
    return results
```

### Inspect 操作

```python
def execute_inspect_wp_A(arm_interface):
    """Inspect workpiece A quality."""
    results = {}
    start_time = time.time()

    # 1. 移动到检测位
    arm_interface.move_to(4.0, 0.0, 0.5)

    # 2. 视觉检测
    vision_data = arm_interface.check_sensor('vision')

    defect_score = vision_data.get('defect_score', 0.0)
    results['defect_score'] = defect_score
    results['passed'] = defect_score < 0.1
    results['success'] = True
    results['duration'] = time.time() - start_time
    return results
```

## 参数如何影响代码

同一个操作类型，不同参数生成不同代码：

| 参数 | 影响 |
|------|------|
| `target_position` | `move_to()` 的坐标 |
| `grip_force` | `grip(force=...)` 的力值 |
| `assembly_force` | 力传感器阈值 |
| `speed` | 各移动原语的速度参数 |
| `stiffness` | `set_compliance()` 的刚度值 |

## 基于反馈的代码精炼

当任务执行失败时，系统可以基于反馈重新生成代码：

```python
feedback = {
    "original_code": "...",
    "execution_result": {"success": False, "error": "Grip force too low"},
    "error": "Grip force too low",
}

new_code = generator.generate(
    task_name="pick_wp_A",
    operation_type="pick",
    arm_id="arm_001",
    required_capabilities=["pick"],
    feedback=feedback,  # 触发精炼模式
)
```

LLM模式下，系统会将失败原因传给LLM要求改进；模板模式下，系统会调整力控参数重试。

## 代码验证

生成的代码会经过基本验证：

```python
# 语法检查
compile(code, '<generated>', 'exec')

# 原语使用检查
assert "arm_interface.move_to(" in code
assert "arm_interface.grip(" in code
```
