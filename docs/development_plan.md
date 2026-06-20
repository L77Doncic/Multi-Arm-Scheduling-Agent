# 开发计划 (Development Plan)

## 项目概述

**项目名称**：基于LLM与Harness Engineering的多机械臂调度智能体代码生成与仿真验证系统

**开发周期**：预计8-10周

**技术栈**：Python 3.10+, DeepSeek-V4-Flash (ModelScope API), Isaac Sim/Omniverse/Isaac Lab

---

## 完成状态总览

| 阶段 | 状态 | 完成度 |
|------|------|--------|
| 第一阶段：基础框架搭建 | ✅ 完成 | 100% |
| 第二阶段：Harness框架核心实现 | ✅ 完成 | 100% |
| 第三阶段：仿真接口开发 | ✅ 完成 | 100% |
| 第四阶段：评估系统开发 | ✅ 完成 | 100% |
| 第五阶段：集成测试与文档 | ⚠️ 部分 | 80% |

### 1.1 LLM集成模块 ⭐ 优先级：高

**目标**：实现与LLM的稳定通信，支持多模型切换

**任务清单**：
- [ ] 实现OpenAI API集成 (`src/agent/llm_clients/openai_client.py`)
- [ ] 实现Anthropic API集成 (`src/agent/llm_clients/anthropic_client.py`)
- [ ] 设计统一的LLM接口抽象类 (`src/agent/llm_clients/base.py`)
- [ ] 实现API密钥管理和配置加载
- [ ] 添加请求重试和错误处理机制
- [ ] 实现token计数和成本追踪

**交付物**：
- LLM客户端模块
- 单元测试覆盖
- API调用示例脚本

### 1.2 提示词工程模块

**目标**：设计高效的提示词模板，用于任务分解和代码生成

**任务清单**：
- [ ] 设计任务分解提示词模板 (`src/agent/prompts/task_decomposition.py`)
- [ ] 设计资源分配提示词模板 (`src/agent/prompts/resource_allocation.py`)
- [ ] 设计代码生成提示词模板 (`src/agent/prompts/code_generation.py`)
- [ ] 实现提示词模板管理器
- [ ] 建立提示词版本控制机制

**交付物**：
- 提示词模板库
- 提示词测试用例

---

## 第二阶段：Harness框架核心实现 (Week 3-4)

### 2.1 任务分解模块

**目标**：实现自然语言指令到结构化任务的自动分解

**任务清单**：
- [ ] 实现自然语言解析器 (`src/harness/task_decomposer.py`)
- [ ] 设计任务依赖关系图数据结构
- [ ] 实现操作类型识别算法
- [ ] 实现任务优先级排序
- [ ] 添加任务分解结果验证

**关键算法**：
```python
# 任务分解流程
instruction -> NLP解析 -> 操作识别 -> 依赖分析 -> 任务结构化
```

**交付物**：
- 任务分解模块完整实现
- 测试用例覆盖多种指令类型

### 2.2 资源分配模块

**目标**：实现智能的机械臂-任务匹配算法

**任务清单**：
- [ ] 实现机械臂能力评估器 (`src/harness/resource_allocator.py`)
- [ ] 设计任务-资源匹配算法
- [ ] 实现负载均衡策略
- [ ] 实现冲突检测机制
- [ ] 添加资源分配优化（基于makespan最小化）

**算法选择**：
- 贪心算法（快速分配）
- 遗传算法（全局优化）
- LLM辅助决策（复杂场景）

**交付物**：
- 资源分配模块
- 性能对比测试

### 2.3 结果验证模块

**目标**：验证仿真执行结果是否符合预期

**任务清单**：
- [ ] 实现仿真结果解析器 (`src/harness/result_validator.py`)
- [ ] 设计约束满足检查器
- [ ] 实现性能指标计算器
- [ ] 实现结果可视化报告生成
- [ ] 添加异常结果标记和日志

**验证维度**：
- 任务完成度验证
- 时间约束验证
- 空间约束验证
- 资源约束验证

**交付物**：
- 结果验证模块
- 验证报告模板

### 2.4 异常处理模块

**目标**：实现系统异常的自动检测和恢复

**任务清单**：
- [ ] 实现异常检测器 (`src/harness/exception_handler.py`)
- [ ] 设计异常分类体系
- [ ] 实现自动恢复策略
- [ ] 实现人工干预接口
- [ ] 添加异常统计和分析

**异常类型**：
- 任务执行超时
- 资源冲突
- 碰撞检测
- 通信中断
- 仿真异常

**交付物**：
- 异常处理模块
- 异常处理策略文档

### 2.5 闭环反馈机制

**目标**：建立仿真结果到调度策略的实时反馈通道

**任务清单**：
- [ ] 实现反馈数据采集器 (`src/harness/feedback_loop.py`)
- [ ] 设计策略调整算法
- [ ] 实现实时参数更新
- [ ] 实现历史数据存储
- [ ] 添加反馈效果评估

**反馈流程**：
```
仿真执行 -> 结果采集 -> 性能分析 -> 策略调整 -> 重新调度
```

**交付物**：
- 闭环反馈模块
- 反馈效果分析报告

---

## 第三阶段：仿真接口开发 (Week 5-6)

### 3.1 Isaac Sim接口

**目标**：实现与NVIDIA Isaac Sim的稳定连接

**任务清单**：
- [ ] 实现Isaac Sim API封装 (`src/simulation/isaac_sim.py`)
- [ ] 实现场景加载和初始化
- [ ] 实现机械臂控制接口
- [ ] 实现仿真状态监控
- [ ] 实现仿真数据记录

**关键功能**：
- 场景创建和加载
- 机械臂运动控制
- 碰撞检测
- 物理仿真参数配置

**交付物**：
- Isaac Sim接口模块
- 仿真环境配置文档

### 3.2 场景构建器

**目标**：实现产线场景的自动化构建

**任务清单**：
- [ ] 实现场景配置解析器 (`src/simulation/scene_builder.py`)
- [ ] 设计场景模板系统
- [ ] 实现工件和夹具生成
- [ ] 实现传送带和工作站布局
- [ ] 添加场景验证和调试工具

**场景要求**：
- 不少于4个操作节点
- 不少于2个工件
- 支持多种布局配置

**交付物**：
- 场景构建模块
- 预定义场景配置文件

### 3.3 备选仿真接口

**目标**：提供Isaac Sim的备选方案

**任务清单**：
- [ ] 实现Omniverse接口 (`src/simulation/omniverse.py`)
- [ ] 实现Isaac Lab接口 (`src/simulation/isaac_lab.py`)
- [ ] 设计统一的仿真接口抽象
- [ ] 实现接口切换机制

**交付物**：
- 多仿真平台支持
- 接口对比文档

---

## 第四阶段：评估系统开发 (Week 7-8)

### 4.1 评估指标模块

**目标**：实现全面的性能评估指标计算

**任务清单**：
- [ ] 实现Makespan计算 (`src/evaluation/metrics.py`)
- [ ] 实现任务成功率计算
- [ ] 实现资源利用率计算
- [ ] 实现约束违反次数统计
- [ ] 实现综合评分算法

**指标定义**：
| 指标 | 计算公式 | 目标 |
|------|----------|------|
| Makespan | max(任务完成时间) | 最小化 |
| 任务成功率 | 成功任务数/总任务数 | 最大化 |
| 资源利用率 | 忙碌时间/总时间 | 最大化 |
| 约束违反次数 | 违反约束的累计次数 | 最小化 |

**交付物**：
- 评估指标模块
- 指标计算文档

### 4.2 基准测试模块

**目标**：实现与基准方法的对比测试

**任务清单**：
- [ ] 实现MRTA-Benchmark数据集加载 (`src/evaluation/benchmark.py`)
- [ ] 实现哈工大数据集加载
- [ ] 设计对比实验框架
- [ ] 实现统计显著性检验
- [ ] 实现结果排名和分析

**基准方法**：
- 随机调度
- 贪心调度
- 传统优化算法（遗传算法、模拟退火等）

**交付物**：
- 基准测试模块
- 对比实验脚本

### 4.3 可视化模块

**目标**：实现评估结果的可视化展示

**任务清单**：
- [ ] 实现调度甘特图 (`src/evaluation/visualizer.py`)
- [ ] 实现资源利用率图表
- [ ] 实现性能对比柱状图
- [ ] 实现仿真过程动画
- [ ] 实现HTML报告生成

**交付物**：
- 可视化模块
- 示例报告

---

## 第五阶段：集成测试与文档 (Week 9-10)

### 5.1 系统集成

**目标**：完成各模块的集成和联调

**任务清单**：
- [ ] 模块间接口联调
- [ ] 端到端流程测试
- [ ] 性能瓶颈分析和优化
- [ ] 内存泄漏检测和修复
- [ ] 并发稳定性测试

### 5.2 数据集准备

**目标**：准备完整的测试数据集

**任务清单**：
- [ ] 下载MRTA-Benchmark数据集
- [ ] 下载哈工大工业智能数据集
- [ ] 数据预处理和格式转换
- [ ] 设计测试场景配置
- [ ] 建立数据集版本管理

### 5.3 文档编写

**目标**：完成项目文档

**任务清单**：
- [ ] Harness框架设计文档 (`docs/design/harness_design.md`)
- [ ] API参考文档 (`docs/design/api_reference.md`)
- [ ] 用户使用手册 (`docs/user_manual.md`)
- [ ] 开发者指南 (`docs/developer_guide.md`)
- [ ] 仿真测试报告模板 (`docs/reports/simulation_report.md`)
- [ ] 评估对比报告模板 (`docs/reports/evaluation_report.md`)

### 5.4 演示准备

**目标**：准备项目演示材料

**任务清单**：
- [ ] 录制仿真演示视频
- [ ] 制作PPT演示文稿
- [ ] 准备代码走读材料
- [ ] 编写演示脚本

---

## 技术风险与应对

| 风险 | 影响 | 应对策略 |
|------|------|----------|
| LLM API调用延迟 | 调度实时性下降 | 实现本地缓存、批量调用优化 |
| 仿真环境配置复杂 | 开发进度受阻 | 提供Docker镜像、详细配置文档 |
| 任务分解准确率低 | 系统可用性差 | 多轮迭代优化提示词、人工校验机制 |
| 资源分配冲突 | 仿真失败 | 实现冲突检测和自动解决机制 |
| 数据集格式不兼容 | 测试无法进行 | 实现数据转换适配器 |

---

## 里程碑节点

| 里程碑 | 时间 | 交付物 | 验收标准 |
|--------|------|--------|----------|
| M1: LLM集成完成 | Week 2 | LLM客户端模块 | API调用测试通过 |
| M2: Harness框架完成 | Week 4 | 核心模块实现 | 单元测试覆盖率>80% |
| M3: 仿真接口完成 | Week 6 | Isaac Sim接口 | 仿真场景可运行 |
| M4: 评估系统完成 | Week 8 | 评估模块 | 指标计算正确 |
| M5: 系统集成完成 | Week 10 | 完整系统 | 端到端测试通过 |

---

## 开发规范

### 代码规范
- 遵循PEP 8代码风格
- 使用Type Hints
- 函数和类必须有docstring
- 单元测试覆盖率>80%

### 版本控制
- 使用Git进行版本管理
- 主分支：main
- 开发分支：dev
- 功能分支：feature/xxx
- 修复分支：fix/xxx

### 提交规范
```
<type>(<scope>): <subject>

类型：
- feat: 新功能
- fix: 修复bug
- docs: 文档更新
- style: 代码格式调整
- refactor: 重构
- test: 测试相关
- chore: 构建/工具相关
```

### 代码审查
- 所有PR需要至少1人审查
- 测试必须通过
- 文档必须同步更新

---

## 资源需求

### 硬件资源
- NVIDIA GPU (RTX 3080或更高) 用于仿真
- 16GB+ 内存
- 100GB+ 存储空间

### 软件资源
- Python 3.10+
- Isaac Sim 2023.1+
- OpenAI/Anthropic API密钥
- Git

### 人力资源
- 主要开发人员：1-2人
- 技术指导：1人
- 测试人员：1人（可兼任）

---

## 附录：文件结构

```
Multi-Arm-Scheduling-Agent/
├── src/
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── core.py                    # 智能体核心
│   │   ├── planner.py                 # 任务规划器
│   │   ├── code_generator.py          # 代码生成器
│   │   ├── llm_clients/               # LLM客户端
│   │   │   ├── __init__.py
│   │   │   ├── base.py               # 抽象基类
│   │   │   ├── openai_client.py      # OpenAI实现
│   │   │   └── anthropic_client.py   # Anthropic实现
│   │   └── prompts/                   # 提示词模板
│   │       ├── __init__.py
│   │       ├── task_decomposition.py
│   │       ├── resource_allocation.py
│   │       └── code_generation.py
│   ├── harness/
│   │   ├── __init__.py
│   │   ├── task_decomposer.py         # 任务分解
│   │   ├── resource_allocator.py      # 资源分配
│   │   ├── result_validator.py        # 结果验证
│   │   ├── exception_handler.py       # 异常处理
│   │   └── feedback_loop.py           # 闭环反馈
│   ├── simulation/
│   │   ├── __init__.py
│   │   ├── isaac_sim.py              # Isaac Sim接口
│   │   ├── omniverse.py              # Omniverse接口
│   │   ├── isaac_lab.py              # Isaac Lab接口
│   │   └── scene_builder.py          # 场景构建器
│   └── evaluation/
│       ├── __init__.py
│       ├── metrics.py                 # 评估指标
│       ├── benchmark.py               # 基准测试
│       └── visualizer.py             # 可视化
├── configs/
│   ├── agent_config.yaml
│   ├── simulation_config.yaml
│   └── evaluation_config.yaml
├── docs/
│   ├── design/
│   │   ├── architecture.md
│   │   ├── harness_design.md
│   │   └── api_reference.md
│   └── reports/
│       ├── simulation_report.md
│       └── evaluation_report.md
├── tests/
│   ├── unit/
│   └── integration/
├── scripts/
│   ├── setup.sh
│   ├── run_simulation.py
│   └── evaluate.py
├── data/
│   ├── datasets/
│   └── scenarios/
├── outputs/
│   ├── videos/
│   ├── logs/
│   └── results/
├── requirements.txt
├── setup.py
└── README.md
```
