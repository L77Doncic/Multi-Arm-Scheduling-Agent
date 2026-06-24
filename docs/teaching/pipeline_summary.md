# 核心流程速查表

## 一句话概括

**用户说一句话 → 系统拆任务 → 分机械臂 → 生成代码 → 跑仿真 → 看结果 → 自动优化 → 再跑**

---

## 6步流水线

| 步骤 | 模块 | 输入 | 输出 | 代码位置 |
|------|------|------|------|----------|
| ① 任务分解 | TaskPlanner | 自然语言指令 | 任务列表 + DAG | `agent/planner.py` |
| ② 资源分配 | ResourceAllocator | 任务列表 + 机械臂列表 | 任务→机械臂映射 | `harness/resource_allocator.py` |
| ③ 代码生成 | CodeGenerator | 任务描述 + 场景参数 | Python控制代码 | `agent/code_generator.py` |
| ④ 仿真执行 | IsaacSimInterface | 生成的代码 | 执行结果 | `simulation/isaac_sim.py` |
| ⑤ 结果验证 | ResultValidator | 执行结果 | 验证报告 | `harness/result_validator.py` |
| ⑥ 反馈调整 | FeedbackLoop | 执行结果 | 策略参数更新 | `harness/feedback_loop.py` |

---

## 9个原子原语

```python
move_to(x, y, z)           # 移动到位置
grip(force)                 # 抓取
release()                   # 释放
rotate(roll, pitch, yaw)    # 旋转
linear_move(dx, dy, dz)     # 相对移动
wait(duration)              # 等待
check_sensor(type)          # 读传感器
set_payload(mass)           # 设负载
set_compliance(x, y, z)     # 设柔顺性
```

---

## 反馈调整的6个参数

| 参数 | 含义 | 什么时候调 | 调到哪里 |
|------|------|------------|----------|
| `timeout_adjustment` | 超时倍数 | 性能差 | ResourceAllocator |
| `retry_count` | 重试次数 | 成功率低 | ExceptionHandler |
| `resource_weight` | 资源权重 | 过载 | ResourceAllocator |
| `priority_boost` | 优先级提升 | 频繁失败 | ResourceAllocator |
| `speed_factor` | 速度系数 | 失败率高→降低 | CodeGenerator |
| `force_factor` | 抓取力系数 | 失败率高→增加 | CodeGenerator |

---

## 关键设计

1. **LLM回退**：有LLM用LLM，没有用模板规则
2. **物理仿真**：Isaac Sim 4.5 + PhysX + Franka Panda USD模型
3. **动态组合**：不是固定技能库，是原语动态组合
4. **闭环优化**：每次执行都调整下次的参数

---

## 文件结构

```
agent/core.py          → 主控流水线
agent/planner.py       → 任务分解
agent/code_generator.py → 代码生成
harness/resource_allocator.py → 资源分配
harness/feedback_loop.py      → 反馈闭环
harness/exception_handler.py  → 异常处理
simulation/isaac_sim.py       → 物理仿真
evaluation/metrics.py         → 指标计算
```
