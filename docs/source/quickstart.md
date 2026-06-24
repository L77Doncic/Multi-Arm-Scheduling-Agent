# Quickstart

本指南帮助你安装并运行多机械臂调度系统。

## 环境要求

| 要求 | 最低配置 | 推荐配置 |
|------|----------|----------|
| Python | ≥ 3.10 | 3.10 |
| GPU | NVIDIA RTX 3070 (8GB) | RTX 5090 (32GB) |
| CUDA | ≥ 11.7 | 13.0 |
| RAM | 32GB | 64GB+ |
| OS | Ubuntu 20.04/22.04 | Ubuntu 22.04 |
| 存储 | 50GB SSD | 100GB+ SSD |

## 安装

```bash
# 克隆仓库
git clone https://github.com/L77Doncic/Multi-Arm-Scheduling-Agent.git
cd Multi-Arm-Scheduling-Agent

# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
pip install -e .

# 安装 Isaac Sim（需要NVIDIA RTX GPU）
pip install isaacsim
```

## 运行仿真

```bash
# 使用 Isaac Sim（需要GPU）
python scripts/run_simulation.py --scenario data/scenarios/1p_production_line.json

# 指定场景和种子
python scripts/_run_single.py data/scenarios/2p_production_line.json 42 outputs/experiments
```

## 运行测试

```bash
python -m pytest tests/unit/test_basic.py -v
```

## 场景配置

系统提供6个生产线场景（基于MRTA-Benchmark格式）：

| 场景 | 说明 | 最优Makespan |
|------|------|:------------:|
| 1p_production_line.json | MRTA实例1p，2工件，4工位，3机械臂 | 584.9s |
| 2p_production_line.json | MRTA实例2p，2工件，4工位，3机械臂 | 931.0s |
| 3p_production_line.json | MRTA实例3p，2工件，4工位，3机械臂 | 642.8s |
| 4p_production_line.json | MRTA实例4p，2工件，4工位，3机械臂 | 465.0s |
| 5p_production_line.json | MRTA实例5p，2工件，4工位，3机械臂 | 490.9s |
| 6p_production_line.json | MRTA实例6p，2工件，4工位，3机械臂 | 489.8s |
