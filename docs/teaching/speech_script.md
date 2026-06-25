# 多机械臂调度智能体 — 演讲稿

> 逐页逐句的演讲脚本，事无巨细，可直接照读。

---

## 第1页：封面

各位老师好，我今天汇报的题目是"多机械臂调度智能体"。这是一个LLM驱动的、在Harness约束框架下运行的多机械臂协同调度系统。我会从项目概述、Harness框架详解、实验结果分析、遇到的问题、以及总结展望这几个方面来汇报。

---

## 第2页：项目概述

首先介绍项目概述。

我们这个系统要解决的核心问题是：给定一个自然语言指令，比如"3个工件需要在4个工位组装，3个机械臂协作完成"，系统能自动完成从任务分解到仿真执行的全流程。

整个系统的流水线分为6步：

第一步，任务分解。系统接收自然语言指令和场景配置，把一段话拆解成一个个具体的、可执行的子任务。比如"取工件A放到工位1"、"对工位1的工件进行组装"。

第二步，资源分配。把每个任务分配给一个具体的机械臂。分配的依据是能力匹配、负载均衡和优先级。

第三步，代码生成。为每个机械臂生成一段Python控制代码。这段代码是由9个原子技能原语动态组合而成的，不是从固定模板复制的。

第四步，仿真执行。在Isaac Sim物理仿真器里实际执行生成的代码，用Franka Panda机械臂模型进行真实物理仿真。

第五步，反馈调整。每次执行的结果都会反馈到FeedbackLoop，分析成功率、耗时、错误模式，然后自动调整策略参数。

第六步，输出指标。计算最终的makespan、成功率、资源利用率等。

左边这个是Harness Engineering框架的5个核心模块：TaskDecomposer负责任务分解，ResourceAllocator负责资源分配，ResultValidator负责结果验证，ExceptionHandler负责异常处理，FeedbackLoop负责闭环反馈。右边是技术栈，包括Isaac Sim 4.5物理仿真、Jacobian IK逆运动学控制、9个原子原语、Omni Replicator帧捕获、MRTA旅行时间矩阵、以及MILP最优基准对比。

---

## 第3页：Harness Engineering详解

接下来是本次汇报的重点——Harness Engineering框架。

Harness Engineering是我们系统的核心"大脑"，它由5个模块组成，负责约束调度、异常处理和自我优化。

第一个模块是TaskDecomposer，任务分解。它接收自然语言指令和场景配置，输出结构化的子任务列表和依赖DAG图。如果系统配置了LLM，就用LLM来智能拆解；如果没有LLM API，就用模板规则兜底。每个子任务都包含operation_type（操作类型）、required_capabilities（需要的能力）、dependencies（依赖关系）、estimated_duration（预估耗时）这些关键数据。

第二个模块是ResourceAllocator，资源分配。它接收任务列表和机械臂列表，输出任务到机械臂的映射表。分配算法是贪心的，评分公式是：capability_weight乘以能力匹配度，加上workload_weight乘以（1减去负载率），加上priority_weight乘以任务优先级，再加上parallel_weight乘以并行机会评分。默认权重是能力匹配60%、负载均衡30%、优先级10%、并行30%。

ResourceAllocator还有一个重要的功能是冲突检测。它能检测4种冲突：TEMPORAL时间冲突（同一机械臂任务过多）、CAPABILITY能力不足（机械臂没有需要的能力）、RESOURCE资源竞争（两个任务争用同一工位）、COLLISION碰撞风险（两个机械臂路径交叉）。检测到冲突后，系统会把低优先级的任务重新分配到其他机械臂，最多迭代10轮。

第三个模块是ResultValidator，结果验证。它检查时间约束、空间约束、资源约束和依赖约束，输出is_valid和violations列表。

第四个模块是ExceptionHandler，异常处理。它能处理7种异常类型：TIMEOUT超时、RESOURCE_CONFLICT资源冲突、COLLISION碰撞、COMMUNICATION_FAILURE通信故障、SIMULATION_ERROR仿真错误、CODE_GENERATION_ERROR代码生成错误、CONSTRAINT_VIOLATION约束违规。

针对每种异常，系统有4种恢复策略：RETRY重试、SKIP跳过、FALLBACK降级、REPLAN重规划。比如TIMEOUT超时，如果重试次数没到上限就RETRY，到上限就SKIP。COLLISION碰撞就REPLAN重规划换路径。SIMULATION_ERROR仿真错误就FALLBACK降级到模板代码。

第五个模块是FeedbackLoop，反馈闭环。这是整个系统最关键的部分。它分析执行结果的成功率、耗时分布、错误模式，然后调整6个参数：

- timeout_adjustment：超时倍数，性能差时乘以1.2放宽超时
- retry_count：重试次数，成功率低时加1
- resource_weight：资源分配权重，机械臂过载时加0.1让分配更均衡
- priority_boost：优先级提升，频繁失败的任务提升优先级
- speed_factor：代码生成速度系数，失败率高时乘以0.8让动作更慢更稳
- force_factor：抓取力系数，失败率高时乘以1.15抓得更紧

这6个参数调整后，会应用到ResourceAllocator、ExceptionHandler、CodeGenerator三个模块，形成闭环。

---

## 第4页：Harness详解（续）

这一页更详细地展示了ResourceAllocator的冲突检测和解决流程。

左边是4种冲突类型的表格。TEMPORAL是时间冲突，比如同一机械臂任务过多。CAPABILITY是能力不足，比如机械臂没有pick能力。RESOURCE是资源竞争，比如两个任务争用同一工位。COLLISION是碰撞风险，比如两个机械臂路径交叉。

右边是分配算法的伪代码。对每个任务，找到所有能力匹配的机械臂，然后按评分排序选择最优的。评分由四部分组成：能力匹配度、负载均衡度、任务优先级、并行机会。分配完成后，如果检测到冲突，就把低优先级的任务重新分配到其他机械臂，最多迭代10轮。

并行机会评分是本次新增的功能。它鼓励将独立的任务分配到不同的机械臂上，从而实现并行执行。评分逻辑是：如果一个任务能和已经分配到其他机械臂上的任务并行执行，就给它更高的分数。

下面是ExceptionHandler的决策树。系统先对异常进行分类，然后根据类型选择恢复策略。TIMEOUT超时就重试，到上限就跳过。COLLISION碰撞就重规划。SIMULATION_ERROR仿真错误就降级到模板代码。每次处理完都会记录历史，用于后续的统计分析。

右边是FeedbackLoop的参数调整规则表。每一行对应一个触发条件和调整方式。比如成功率低于80%就放宽超时，机械臂过载就增加资源权重让分配更均衡。

---

## 第5页：已完成内容

接下来汇报已完成的内容。

第一，完整的Pipeline已经打通。从自然语言指令到任务分解、资源分配、代码生成、仿真执行、反馈调整、输出指标，全链路都能运行。

第二，Harness框架的5个模块已经实现。TaskDecomposer、ResourceAllocator、ResultValidator、ExceptionHandler、FeedbackLoop，闭环反馈已经可以工作。

第三，MRTA旅行时间矩阵已实现。我们加载了MRTA-Benchmark的T_t矩阵，用于计算机械臂间的移动时间。这让实验结果更接近真实的MRTA基准。

第四，真实LLM API已接入。我们使用了mimo-v2.5模型，通过HTTP API直接调用，避免了OpenAI SDK的兼容性问题。

第五，Isaac Sim集成已经完成。使用Franka Panda USD模型、IK控制、PhysX物理引擎、Ground Plane、Omni Replicator帧捕获。

第六，视频录制功能已经实现。支持ffmpeg H.264编码、5倍慢动作回放、多场景批量录制。

第七，MRTA-Benchmark实验已经完成。6个场景、5种子实验、平均成功率94%。

---

## 第6页：实验结果

接下来展示实验结果。

我们一共跑了6个场景的实验，每个场景5个随机种子。引入MRTA旅行时间后，实验结果更接近真实的MRTA基准。

具体数据如下：

1p场景：8个任务，Makespan 247.4秒，最优Makespan 584.9秒，比率0.42x，资源利用率34%，成功率100%。

2p场景：8个任务，Makespan 885.9秒，最优Makespan 931.0秒，比率0.95x，资源利用率33%，成功率88%。

3p场景：8个任务，Makespan 757.2秒，最优Makespan 642.8秒，比率1.18x，资源利用率39%，成功率100%。

4p场景：8个任务，Makespan 750.0秒，最优Makespan 465.0秒，比率1.61x，资源利用率38%，成功率100%。

5p场景：8个任务，Makespan 311.7秒，最优Makespan 490.9秒，比率0.64x，资源利用率35%，成功率100%。

6p场景：8个任务，Makespan 818.2秒，最优Makespan 489.8秒，比率1.67x，资源利用率33%，成功率75%。

平均比率1.08x，平均成功率94%，平均资源利用率35%。

这里需要说明一下，引入MRTA旅行时间后，我们的Makespan与MRTA基准非常接近（平均1.08x）。部分场景（3p/4p/6p）略长于基准，这是因为我们的启发式调度方法不是全局最优，而MRTA基准使用MILP求解器找全局最优解。

---

## 第6b页：实验数据分析

这一页是对实验数据的深入分析。

首先看第一个结论：引入MRTA旅行时间后，结果接近基准。平均Makespan比率为1.08x，非常接近MRTA基准。这说明加入移动时间后，我们的调度与MRTA最优解基本持平。改进前（无移动时间），比率在0.07x到0.30x之间，严重低估实际耗时。改进后（含移动时间），比率在0.42x到1.67x之间，更接近真实场景。

第二个发现是部分场景超过基准的原因。3p（1.18x）、4p（1.61x）、6p（1.67x）长于MRTA基准。这是因为MRTA基准用MILP求解器找全局最优，我们用启发式规则。启发式方法在复杂场景下不够优化，但结果仍然可行。

第三个发现是资源利用率仍需改进。平均资源利用率为35%，33%等于只有1台机器人在干活（1/3约等于33.3%）。这说明当前调度倾向于单臂串行执行，多臂并行调度能力不足。这是下一阶段优化的核心方向。

第四个发现是LLM接入后成功率94%。接入真实LLM API后，任务分解和代码生成质量提升。平均成功率为94%。LLM能更好地理解任务语义，生成更合理的调度方案。但仍有6%的失败率，需要进一步优化。

---

## 第7页：遇到的问题

接下来汇报遇到的问题，这些问题目前仍然存在。

第一个严重问题是物理抓取不真实。工件通过"传送+冻结"的方式附着到夹爪，不是真正的物理仿真。FixedJoint在Isaac Sim pip包中API受限，无法实现真正的物理绑定。

第二个严重问题是视频演示异常。视频中只拍到两个机械臂，应该有三个。工件没有被夹取，机械臂运动轨迹混乱，画面不连贯。

第三个严重问题是Isaac Sim进程崩溃。app.close()调用sys.exit()导致SIGSEGV段错误。每个实验必须用独立子进程加os._exit(0)来避免。

第四个问题是串流限制。Livestream Clients仅支持同局域网的UDP传输。SSH只能转发TCP，无法传输UDP信号。Web流媒体需要Docker环境。

第五个问题是Docker无法使用。一是系统盘30G太小，无法同时装下venv和Docker镜像。二是autodl本身就是一个Ubuntu容器，在容器内又尝试拉取并运行新的Docker镜像，解压镜像层时containerd需要创建overlayfs挂载点，但容器默认不具备宿主机内核的挂载权限，无法正常拉取和运行嵌套容器。

第六个问题是环境损坏。conda升级破坏了miniconda3的Isaac Sim 6.0环境，simulation_app扩展丢失。Isaac Sim 4.5和6.0版本不兼容。

第七个问题是磁盘空间不足。系统盘30G，Isaac Sim依赖（nvidia 4.1G + torch 1.7G）占大量空间，conda升级后只剩1.1G可用。

第八个问题是网络受限。Docker Hub、阿里云、腾讯、网易镜像源均无法拉取。无法安装更新的Isaac Sim版本。

第九个问题是视频黑帧和相机问题。Replicator帧捕获需要render=True，相机位置过近导致机械臂在画面外，地面无Ground Plane导致工件穿透。

第十个问题是资源利用率偏低。33%的利用率意味着只有1台机器人在干活，多臂并行调度能力不足。这是调度算法的设计问题，需要改进。

---

## 第8页：尝试的方法

针对这些问题，我们尝试了多种解决方法。

FixedJoint物理抓取：我们用UsdPhysics.FixedJoint来绑定工件到夹爪。测试发现Isaac Sim 4.5的API可用，有GetBody0Rel和GetBody1Rel方法，但需要正确的扩展版本。这个方法部分成功。

Isaac Sim环境修复：我们从venv复制simulation_app到miniconda3，但发现4.5与6.0版本不兼容，依赖的omni.kit.usd模块不同。这个方法失败。

升级libstdc++：通过conda安装libstdcxx-ng=13修复GLIBCXX_3.4.30依赖。成功但引发了连锁依赖问题。

Docker容器化：安装Docker到数据盘，但网络受限无法拉取镜像，而且autodl是容器，无法嵌套Docker，缺少overlayfs权限。失败。

视频优化：添加Ground Plane、DomeLight照明、调整相机位置、ffmpeg H.264编码、5倍慢动作。成功。

子进程隔离：每个实验用独立子进程运行，用os._exit(0)避免Isaac Sim崩溃。成功。

MRTA旅行时间：实现mrta_travel.py模块，加载MRTA T_t矩阵，将移动时间纳入Makespan计算。成功。

真实LLM API：接入mimo-v2.5模型，使用HTTP API避免OpenAI SDK兼容性问题。成功。

并行任务调度：修改task_decomposer支持跨工件并行，修改resource_allocator添加并行机会评分。部分成功（分配改善，但执行逻辑仍是顺序的）。

---

## 第9页：系统架构

这是系统的代码结构。

src/目录下有4个包：

agent/是智能体核心。core.py是主控流水线，planner.py是任务分解（支持跨工件并行），code_generator.py是代码生成（9个原子原语动态组合），llm_clients/是LLM客户端抽象。

harness/是Harness Engineering框架。task_decomposer.py负责NL到结构化子任务和依赖DAG，resource_allocator.py负责贪心能力匹配、4种冲突检测、负载均衡和并行机会评分，result_validator.py负责时间/空间/资源约束验证，exception_handler.py负责7种异常和4种恢复策略（retry/skip/fallback/replan），feedback_loop.py负责6参数闭环调整并应用到各模块。

simulation/是仿真后端。base.py定义SimulationInterface抽象基类，isaac_sim.py是Isaac Sim 4.5物理仿真，mrta_travel.py是MRTA旅行时间管理器，arm_interface.py是代码到仿真动作的适配器。

evaluation/是评估指标。metrics.py计算makespan/success_rate/utilization，benchmark.py是MILP最优基准和配对t检验，mrta_loader.py是MRTA-Benchmark数据加载。

---

## 第10页：总结与展望

最后是总结与展望。

核心成果方面：我们实现了完整的Harness约束框架和LLM驱动的调度Pipeline，完成了6个场景的实验验证。MRTA旅行时间矩阵已实现，真实LLM API已接入。系统在任何环境下都能运行，因为有LLM回退机制。

实验结果方面：引入MRTA旅行时间后，平均Makespan比率为1.08x，接近MRTA基准。平均成功率为94%。资源利用率平均35%，仍有提升空间。

未完全实现的方面：一是物理抓取，FixedJoint绑定工件到夹爪，受限于Isaac Sim pip包API。二是视频演示异常，机械臂运动混乱、相机视角问题。三是Docker容器化，网络受限加嵌套容器权限不足。四是资源利用率偏低，多臂并行调度能力不足。

核心收获方面：Harness Engineering的闭环反馈机制是系统的核心价值。每次执行都自动优化策略参数。5个模块协同工作，形成了自适应调度框架。MRTA旅行时间的引入让实验结果更接近真实场景。

后续方向：一是优化资源分配算法，提升多臂并行率。二是改进启发式方法，接近MRTA全局最优。三是微调LLM提升调度质量。四是修复物理抓取和视频演示问题。

以上就是我的汇报，请老师批评指正，谢谢。
