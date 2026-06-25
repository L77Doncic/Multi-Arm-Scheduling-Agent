# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LLM-driven multi-arm robotic scheduling system. Takes natural language + scene config (YAML), decomposes tasks, allocates resources to robot arms, generates executable code from 9 atomic primitives, runs simulation, collects feedback, and computes metrics.

**Pipeline**: NL → Task Decomposition → Resource Allocation → Code Generation → Simulation → Feedback → Metrics

## Common Commands

```bash
# Install
pip install -r requirements.txt && pip install -e .

# Run simulation (mock backend, no GPU)
python scripts/run_simulation.py --scenario data/scenarios/1p_production_line.json

# Run simulation with specific backend
python scripts/run_simulation.py --scenario data/scenarios/1p_production_line.json --sim isaac

# Tests
python -m pytest tests/ -v
python -m pytest tests/unit/test_basic.py -v                    # single test file
python -m pytest tests/ --cov=src --cov-report=html             # with coverage

# Rigorous evaluation (NeurIPS standard, paired t-test)
python scripts/evaluate_rigorous.py --scenario data/scenarios/1p_production_line.json --runs 5

# MRTA-Benchmark evaluation
python scripts/evaluate.py --dataset data/datasets/MRTA-Benchmark
```

## Architecture

Four packages under `src/`:

**`agent/`** — LLM orchestration core
- `core.py`: `SchedulingAgent` — main orchestrator running the 6-step pipeline. Entry point: `execute_scheduling(instruction, scene_config)` → `ExecutionResult`
- `planner.py`: `TaskPlanner` — LLM or heuristic task decomposition into `TaskNode` DAGs
- `code_generator.py`: `CodeGenerator` — generates Python code from 9 primitives (move_to, grip, release, rotate, linear_move, wait, check_sensor, set_payload, set_compliance)
- `llm_clients/`: provider abstraction — `SyncLLMClient` (default, OpenAI-compatible), `OpenAIClient`, `AnthropicClient`, `LLMClientFactory`
- `prompts/`: LLM prompt templates for task decomposition, code generation, resource allocation

**`harness/`** — Harness Engineering framework (5 modules)
- `task_decomposer.py`: NL → structured subtasks + dependency DAG
- `resource_allocator.py`: greedy capability matching + 4 conflict types + load balancing
- `result_validator.py`: temporal/spatial/resource constraint checking
- `exception_handler.py`: 7 exception types + 4 recovery strategies (retry/skip/fallback/escalate)
- `feedback_loop.py`: closed-loop — analyzes performance, adjusts 6 strategy parameters (timeout, retry_count, resource_weight, priority_boost, speed_factor, force_factor)

**`simulation/`** — Simulation backends
- `base.py`: `SimulationInterface` ABC (initialize, load_scene, execute_action, get_state, step, reset, close)
- `isaac_sim.py`: Isaac Sim 4.5 physics simulation (Franka Panda USD, PhysX, IK control)
- `arm_interface.py`: adapter bridging generated code primitives → simulation backend actions

**`evaluation/`** — Metrics and benchmarking
- `metrics.py`: `MetricsCalculator` — makespan, success rate, utilization, violations
- `benchmark.py`: `BenchmarkRunner` — random/greedy/genetic baselines with paired t-tests
- `mrta_loader.py`: `MRTABenchmarkLoader` — converts APEX-MR LEGO assembly JSON → scenario format
- `visualizer.py`: Gantt charts + HTML reports

## Key Design Patterns

- **LLM fallback**: All LLM-powered components (TaskPlanner, CodeGenerator) fall back to heuristic/template mode when no API key is set. The system is fully functional without an LLM.
- **Simulation backend abstraction**: All backends implement `SimulationInterface`. Switch via `--sim` flag or config — zero code changes in agent/harness.
- **Closed-loop feedback**: Every task execution feeds back into `FeedbackLoop`, which adjusts strategy parameters before the next task. This is not optional — it's core to the system.
- **9 atomic primitives**: Code generation composes from: move_to, grip, release, rotate, linear_move, wait, check_sensor, set_payload, set_compliance.
- **Generated code execution**: `arm_interface.execute_generated_code()` uses Python `exec()` to run generated code, then discovers the `execute_*` function in the namespace and calls it with an `ArmInterface` instance. The generated code calls primitives like `arm_interface.move_to(...)` which translate to simulation actions.
- **Code regeneration on failure**: When a task fails during execution, the system regenerates code with adjusted speed/force factors (speed ↓ 15%, force ↑ 10%) and retries up to `retry_count` times. This is driven by both the feedback loop's global adjustments and per-task regeneration in `core.py:_execute_tasks()`.
- **Feedback adjustment routing**: The feedback loop adjusts 6 parameters routed to specific modules:
  - `timeout_adjustment` → `resource_allocator`
  - `retry_count` → `exception_handler`
  - `resource_weight`, `priority_boost` → `resource_allocator`
  - `code_gen_speed_factor`, `code_gen_force_factor` → `code_generator`
  Each module accepts updates via `update_config()`.
- **MRTA travel times**: Scenario JSON files include `mrta_travel_times` with `T_e` (execution times per task) and `T_t` (travel time matrix). These are loaded by `simulation/mrta_travel.py` and override task durations during execution, making results match the MRTA-Benchmark exactly.
- **LLM client uses raw HTTP**: `SyncLLMClient` sends requests via `requests.post()` directly (not the OpenAI SDK client) to avoid serialization issues. It works with any OpenAI-compatible API endpoint.

## Configuration

Three YAML files in `configs/`:
- `agent_config.yaml`: LLM provider/model/settings, robot arm definitions (capabilities, workspace, payload), task limits, harness feedback/validation/exception config, evaluation metrics
- `simulation_config.yaml`: backend selection, physics settings, mock failure probability, Isaac Sim paths
- `evaluation_config.yaml`: metrics, datasets, baseline methods, statistical settings

API keys via environment variables or `.env` file (see `.env.example`):
- `OPENAI_API_KEY` — for OpenAI-compatible providers (default: Xiaomi MiMo)
- `ANTHROPIC_API_KEY` — for Anthropic provider

## Key Data Classes (src/agent/core.py)

- `Task`: id, name, description, dependencies, status, assigned_arm, operation_type, station_id, workpiece_id, required_capabilities, estimated_duration, priority
- `RobotArm`: id, name, capabilities, max_load, position, is_busy
- `ExecutionResult`: execution_id, instruction, tasks, allocation, makespan, task_success_rate, resource_utilization, constraint_violations, execution_log, feedback_adjustments, generated_codes
- `TaskStatus`: PENDING, IN_PROGRESS, COMPLETED, FAILED, CANCELLED

## Testing Notes

Tests use `sys.path.insert(0, ...)` to add `src/` to the path (not package imports). Test files are in `tests/unit/`. The end-to-end integration test in `test_basic.py` exercises the full pipeline with IsaacSimInterface.

**Import convention**: Both scripts and tests add `src/` to `sys.path` at the top of the file:
```python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
```
Then import directly: `from agent.core import SchedulingAgent`, `from harness.feedback_loop import FeedbackLoop`, etc. Do not use package-relative imports.

## Scenarios

- `data/scenarios/1p_production_line.json`: 1 workpiece, 4 stations, 3 arms, MILP-optimal makespan 584.9s
- `data/scenarios/2p_production_line.json` - `6p_production_line.json`: 2-6 workpieces, 4 stations, 3 arms
- `data/datasets/MRTA-Benchmark/`: 13 APEX-MR LEGO assembly tasks (RSS 2025)

**Scenario JSON structure**: Each scenario has two top-level keys:
- `scenario`: contains `stations` (id, position, capabilities_required, operation, estimated_duration), `workpieces` (id, initial_position, operations_sequence), `robot_arms` (id, base_position, capabilities, max_payload), `constraints`, `instruction`, and `optimal_schedule` (MILP baseline).
- `mrta_travel_times`: contains `T_e` (execution time per task), `T_t` (NxN travel time matrix), `task_locations`, and `precedence_constraints`. These are loaded by `simulation/mrta_travel.py` and used to override task durations during execution.

## Operation Type Mapping

The system maps natural-language operation types to simulation action types via `_ACTION_TYPE_MAP` in `core.py`. Key mappings:
- `pick`, `pick_workpiece_from_feed`, `pick_brick` → `"pick"`
- `place`, `package`, `output`, `drop` → `"place"`
- `move`, `transfer`, `transport` → `"move"`
- `assemble`, `final_assembly`, `join`, `press_brick` → `"assemble"`
- `inspect`, `quality_inspection`, `verify` → `"inspect"`
- `tighten`, `bolt` → `"move"` (mock doesn't have tighten)
- `weld`, `solder` → `"assemble"`
- Unknown types default to `"move"`.

## Documentation

- `docs/design/architecture.md` — system architecture
- `docs/design/harness_design.md` — harness framework design with interaction diagrams
- `docs/design/api_reference.md` — API docs for 11 core classes
- `data/benchmark_specification.md` — unified benchmark sources and evaluation protocol
