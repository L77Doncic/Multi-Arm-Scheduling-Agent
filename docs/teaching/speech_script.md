# 多机械臂调度智能体

---

## 第1页：封面

朱老师好，我今天会从项目概述、Harness框架详解、实验结果分析、遇到的问题、以及总结展望这几个方面来汇报。

---

## 第2页：项目概述

首先介绍项目概述。

我们这个系统要解决的核心问题是：给定一个自然语言指令，系统能自动完成从任务分解到仿真执行的全流程。

整个系统的流水线分为6步：

第一步，任务分解。系统接收自然语言指令和场景配置，把一段话拆解成一个个具体的、可执行的子任务。比如"取工件A放到工位1"、"对工位1的工件进行组装"。

第二步，资源分配。把每个任务分配给一个具体的机械臂。分配的依据是能力匹配、负载均衡、优先级和并行机会。

第三步，代码生成。为每个机械臂生成一段Python控制代码。这段代码是由9个原子技能原语动态组合而成的，不是从固定模板复制的。

第四步，仿真执行。在PhysXOnlySimulator物理仿真器里实际执行生成的代码，用Franka Panda机械臂模型进行物理仿真计算。

第五步，反馈调整。每次执行的结果都会反馈到FeedbackLoop，分析成功率、耗时、错误模式，然后自动调整策略参数。

第六步，输出指标。计算最终的makespan、成功率、资源利用率等。

左边这个是Harness框架的5个核心模块：TaskDecomposer负责任务分解，ResourceAllocator负责资源分配，ResultValidator负责结果验证，ExceptionHandler负责异常处理，FeedbackLoop负责闭环反馈。右边是仿真模拟，包括PhysXOnlySimulator纯物理计算、逆运动学关节控制、9个原子原语、MRTA旅行时间矩阵、以及MILP最优基准对比。

---

## 第3页：Harness Engineering详解

Harness Engineering是我们系统的核心，它由5个模块组成，负责约束调度、异常处理和自我优化。

第一个模块是TaskDecomposer，任务分解。它接收自然语言指令和场景配置，输出结构化的子任务列表和依赖DAG图。如果系统配置了LLM，就用LLM来智能拆解；如果没有LLM API，就用模板规则兜底。每个子任务都包含operation_type（操作类型）、required_capabilities（需要的能力）、dependencies（依赖关系）、estimated_duration（预估耗时）这些关键数据。

第二个模块是ResourceAllocator，资源分配。它接收任务列表和机械臂列表，输出任务到机械臂的映射表。分配算法是贪心的，评分由四部分组成：能力匹配度（权重46%）、负载均衡度（权重23%）、任务优先级（权重8%）、并行机会评分（权重23%）。这四个权重归一化后总和为100%。

ResourceAllocator还有一个重要的功能是冲突检测。它能检测4种冲突：TEMPORAL时间冲突（同一机械臂任务过多）、CAPABILITY能力不足（机械臂没有需要的能力）、RESOURCE资源竞争（两个任务争用同一工位）、COLLISION碰撞风险（两个机械臂路径交叉）。检测到冲突后，系统会把低优先级的任务重新分配到其他机械臂，最多迭代10轮。

第三个模块是ResultValidator，结果验证。它检查时间约束、空间约束、资源约束和依赖约束，输出is_valid和violations列表。

第四个模块是ExceptionHandler，异常处理。具体来说它能处理7种异常类型：TIMEOUT超时、RESOURCE_CONFLICT资源冲突、COLLISION碰撞、COMMUNICATION_FAILURE通信故障、SIMULATION_ERROR仿真错误、CODE_GENERATION_ERROR代码生成错误、CONSTRAINT_VIOLATION约束违规。

针对每种异常，系统有4种恢复策略：RETRY重试、SKIP跳过、FALLBACK降级、REPLAN重规划。比如TIMEOUT超时，如果重试次数没到上限就RETRY，到上限就REPLAN重规划。COLLISION碰撞就REPLAN重规划换路径。SIMULATION_ERROR仿真错误就FALLBACK降级到模板代码。

第五个模块是FeedbackLoop，反馈闭环。这是整个系统最关键的部分。它分析执行结果的成功率、耗时分布、错误模式，然后调整6个参数：


- timeout_adjustment：超时倍数，性能差时乘以1.2放宽超时。避免因物理仿真卡顿或轻微避障导致任务被强制终止，从而把“慢成功”误判为“失败”。
- retry_count：重试次数，成功率低时加1。它的作用是**提升我们的核心评估指标，任务成功率** 。允许智能体在第一次抓取滑脱后，自动再试一次，而不是直接放弃导致整个 Makespan 报废。
- resource_weight：资源分配权重，机械臂过载时加0.1让分配更均衡。
- priority_boost：优先级提升，频繁失败的任务提升优先级，主要目的是打破死锁。
- speed_factor：代码生成速度系数，失败率高时乘以0.8让动作更慢更稳，以提升稳定性。
- force_factor：抓取力系数，失败率高时乘以1.15抓得更紧，确保工件在搬运路径上不掉落。


这6个参数调整后，会应用到ResourceAllocator、ExceptionHandler、CodeGenerator三个模块，形成闭环。

---

## 第4页：Harness详解（续）

这一页更详细地展示了ResourceAllocator的冲突检测和解决流程。

左边是4种冲突类型的表格。TEMPORAL是时间冲突，比如同一机械臂任务过多。CAPABILITY是能力不足，比如机械臂没有pick能力。RESOURCE是资源竞争，比如两个任务争用同一工位。COLLISION是碰撞风险，比如两个机械臂路径交叉。

右边是分配算法的伪代码。对每个任务，找到所有能力匹配的机械臂，然后按评分排序选择最优的。评分由四部分组成：能力匹配度、负载均衡度、任务优先级、并行机会。分配完成后，如果检测到冲突，就把低优先级的任务重新分配到其他机械臂，最多迭代10轮。

然后是我们的并行机会评分。它鼓励将独立的任务分配到不同的机械臂上，从而实现并行执行。评分逻辑是：如果一个任务能和已经分配到其他机械臂上的任务并行执行，就给它更高的分数。

下面是ExceptionHandler的决策树。系统先对异常进行分类，然后根据类型选择恢复策略。TIMEOUT超时就重试，到上限就跳过。COLLISION碰撞就重规划。SIMULATION_ERROR仿真错误就降级到模板代码。每次处理完都会记录历史，用于后续的统计分析。

右边是FeedbackLoop的参数调整规则表。每一行对应一个触发条件和调整方式。比如成功率低于80%就放宽超时，机械臂过载就增加资源权重让分配更均衡。

---

## 第5页：已完成内容

接下来汇报已完成的内容。总的来说，题目要求的基础内容已经全部完成，并针对实验结果优化了设计和调度。

第一，完整的Pipeline已经打通。从自然语言指令到任务分解、资源分配、代码生成、仿真执行、反馈调整、输出指标，全链路都能运行。

第二，Harness框架的5个模块已经实现。TaskDecomposer、ResourceAllocator、ResultValidator、ExceptionHandler、FeedbackLoop，闭环反馈已经可以工作。

第三，MRTA旅行时间矩阵已实现。我们加载了MRTA-Benchmark的T_t矩阵，用于计算机械臂间的移动时间。这让实验结果更接近真实的MRTA基准。

第四，真实LLM API已接入。我们使用了DeepSeek Chat模型（替代mimo-v2.5，因长prompt超时），通过HTTP API直接调用，避免了OpenAI SDK的兼容性问题。

第五，PhysXOnlySimulator已实现。因容器环境Vulkan驱动不可用，改用纯物理计算+MRTA旅行时间的仿真后端，不依赖Vulkan渲染。使用Franka Panda USD模型、IK控制、PhysX物理引擎。

第六，MRTA-Benchmark实验已经完成。6个场景、每个场景5个种子、共30次实验、平均成功率80%。

---

## 第6页：实验结果

接下来展示实验结果。

我们一共跑了6个场景的实验，每个场景5个随机种子，共30次实验。使用DeepSeek Chat作为LLM后端，PhysXOnlySimulator作为仿真后端。

具体数据如下：

平均Makespan 682.9s，平均比率1.19x，平均成功率80%，平均资源利用率47%。

---

## 第7页：实验数据分析

这一页我们对实验数据的深入分析。

第一个结论：引入MRTA旅行时间后，结果接近基准。平均Makespan比率为1.19x，非常接近MRTA基准。在第一次实验当中我忽略了移动时间，导致结果看起来极佳，但考虑到LLM的分解规划不会所有的实验都比milp算法都快这么多，在分析之后发现是漏了移动时间。在加入移动时间后，我们的调度与MRTA最优解基本持平。改进前（无移动时间），比率在0.07x到0.30x之间，严重低估实际耗时。改进后（含移动时间），比率在0.74x到1.59x之间，更接近真实场景。

第二个发现是部分场景超过基准的原因。3p（1.33x）、4p（1.59x）、5p（1.33x）长于MRTA基准。这是因为MRTA基准用MILP求解器找全局最优，我们用贪心算法，在复杂场景下不够优化，但结果仍然可行。而2p（0.74x）和6p（0.94x）则接近或优于MILP基准。

第三个发现是资源利用率有显著提升。平均资源利用率为47%，相比之前35%有明显改善。这说明三机协同调度能力增强，但仍低于理想水平。

第四个发现是LLM接入后成功率80%。接入DeepSeek Chat LLM后，任务分解和代码生成质量稳定。平均成功率为80%。相比之前94%的成功率有所下降，主要原因是LLM从mimo-v2.5更换为DeepSeek Chat，任务分解质量有所变化。

---

## 第8页：遇到的问题

接下来汇报遇到的问题。

遭遇的问题比较多但毕竟集中，大部分是出现在仿真接口部分，主要有三个大的方面：

第一方面是物理仿真不完全，只有部分是满足物理学定理的。检查之后发现不是harness出现了问题，而是FixedJoint在Isaac Sim pip包中API受限，无法实现真正的物理绑定。但是如果替换版本又回出现simulation_app扩展丢失的问题，导致kit加载顺序出现问题。

第二个方面是Vulkan驱动问题。容器环境中Vulkan驱动不可用，导致Isaac Sim 4.5的完整渲染功能无法启动。排查发现`vulkaninfo`命令失败，Vulkan ICD配置为空。最终改用PhysXOnlySimulator进行纯物理计算，不依赖Vulkan渲染。视频录制也因此无法实现。

第三个方面是Docker容器化和平台限制。autodl平台网络受限无法拉取镜像，而且是容器环境无法嵌套Docker，缺少overlayfs权限。这些限制导致部分问题无法修改和验证。


---

## 第9页：尝试的方法

针对这些问题，我们尝试了多种解决方法。

对于物理抓取：我们用UsdPhysics.FixedJoint来绑定工件到夹爪。测试发现Isaac Sim 4.5的API可用，有GetBody0Rel和GetBody1Rel方法，但需要正确的扩展版本。这个方法部分成功。

Vulkan驱动问题：排查容器环境中Vulkan驱动不可用的问题。检查`vulkaninfo`、NVIDIA驱动、Vulkan ICD配置，发现容器环境限制导致无法正常加载。最终改用PhysXOnlySimulator，纯物理计算+MRTA旅行时间，不依赖Vulkan渲染。成功。

Isaac Sim环境修复：我们从venv复制simulation_app到miniconda3，但发现4.5与6.0版本不兼容，依赖的omni.kit.usd模块不同。这个方法失败。

升级libstdc++：通过conda安装libstdcxx-ng=13修复GLIBCXX_3.4.30依赖。成功但引发了连锁依赖问题。

Docker容器化：安装Docker到数据盘，但网络受限无法拉取镜像，而且autodl是容器，无法嵌套Docker，缺少overlayfs权限。失败。

子进程隔离：每个实验用独立子进程运行，用os._exit(0)避免Isaac Sim崩溃。成功。

MRTA旅行时间：实现mrta_travel.py模块，加载MRTA T_t矩阵，将移动时间纳入Makespan计算。成功。

DeepSeek Chat LLM：接入DeepSeek Chat模型（替代mimo-v2.5，因长prompt超时），使用HTTP API避免OpenAI SDK兼容性问题。成功。

并行任务调度：修改task_decomposer支持跨工件并行，修改resource_allocator添加并行机会评分。部分成功，怀疑是LLM没有经过微调导致的。

---

## 第10页：系统架构

这是系统的代码结构。

---

## 第11页：总结与展望

最后是总结与展望。

核心成果方面：我们实现了完整的Harness约束框架和LLM驱动的调度Pipeline，完成了6个场景30次实验验证。MRTA旅行时间矩阵已实现，DeepSeek Chat LLM API已接入，PhysXOnlySimulator已实现。

实验结果方面：引入MRTA旅行时间后，平均Makespan比率为1.19x，接近MRTA基准。平均成功率为80%。资源利用率平均47%，相比之前有显著提升。

未完全实现的方面：一是物理抓取，FixedJoint绑定工件到夹爪，受限于Isaac Sim pip包API。二是视频录制，因Vulkan驱动不可用已移除。三是Docker容器化，网络受限加嵌套容器权限不足。四是成功率有待提升，需要进一步优化LLM任务分解质量。

核心收获方面：Harness Engineering的闭环反馈机制是系统的核心价值。每次执行都自动优化策略参数。5个模块协同工作，形成了自适应调度框架。MRTA旅行时间的引入让实验结果更接近真实场景。PhysXOnlySimulator证明了在无Vulkan环境下仍能提供可靠仿真。

后续方向：一是优化资源分配算法，提升多臂并行率。二是改进启发式方法，接近MRTA全局最优。三是微调LLM提升调度质量和成功率。四是修复物理抓取问题。

以上就是我的汇报，请老师批评指正，谢谢。
