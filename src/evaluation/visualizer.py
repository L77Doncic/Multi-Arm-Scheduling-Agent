"""
Visualization utilities for multi-arm scheduling evaluation.

Generates Gantt charts, resource-utilization plots, comparison bar
charts, and an HTML report.  All plotting is done with matplotlib;
the HTML report is self-contained (inline CSS/JS, embedded images).
"""

import base64
import io
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import matplotlib
matplotlib.use("Agg")  # non-interactive backend; safe for headless servers

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.figure import Figure

from evaluation.metrics import EvaluationMetrics, ExecutionLog, TaskEntry

logger = logging.getLogger(__name__)

# Colour palette for arms (cycles if >8 arms)
_ARM_COLORS = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
    "#9467bd", "#8c564b", "#e377c2", "#7f7f7f",
]


class Visualizer:
    """
    Create evaluation plots and reports.

    Every public ``plot_*`` method accepts an optional *save_path*; when
    provided the figure is written to disk.  The caller can also retrieve
    the :class:`Figure` object via the ``fig`` attribute after each call.
    """

    def __init__(self, style: str = "seaborn-v0_8-whitegrid") -> None:
        try:
            plt.style.use(style)
        except (OSError, ValueError):
            logger.debug("Matplotlib style '%s' not found; using default", style)
        self.fig: Optional[Figure] = None

    # ------------------------------------------------------------------
    # Gantt chart
    # ------------------------------------------------------------------

    def plot_gantt_chart(
        self,
        execution_log: ExecutionLog,
        save_path: Optional[str] = None,
        title: str = "Task Schedule (Gantt Chart)",
    ) -> None:
        """
        Render a Gantt chart where each horizontal bar is a task and
        the Y axis groups tasks by robot arm.
        """
        if not execution_log.entries:
            logger.warning("Empty execution log; nothing to plot")
            return

        # Group entries by arm
        arms: Dict[str, List[TaskEntry]] = {}
        for entry in execution_log.entries:
            arms.setdefault(entry.arm_id, []).append(entry)

        arm_ids = sorted(arms.keys())
        fig, ax = plt.subplots(figsize=(max(10, len(execution_log) * 0.4), max(4, len(arm_ids) * 0.8)))
        self.fig = fig

        color_map: Dict[str, str] = {}
        for idx, arm_id in enumerate(arm_ids):
            color_map[arm_id] = _ARM_COLORS[idx % len(_ARM_COLORS)]

        for y_pos, arm_id in enumerate(arm_ids):
            entries = sorted(arms[arm_id], key=lambda e: e.start_time)
            for entry in entries:
                duration = entry.end_time - entry.start_time
                color = color_map[arm_id]
                alpha = 1.0 if entry.status == "completed" else 0.4
                bar = ax.barh(
                    y_pos,
                    duration,
                    left=entry.start_time,
                    height=0.6,
                    color=color,
                    alpha=alpha,
                    edgecolor="white",
                    linewidth=0.5,
                )
                # Annotate task id on the bar
                ax.text(
                    entry.start_time + duration / 2,
                    y_pos,
                    entry.task_id,
                    ha="center",
                    va="center",
                    fontsize=7,
                    color="white",
                    fontweight="bold",
                )

        ax.set_yticks(range(len(arm_ids)))
        ax.set_yticklabels(arm_ids)
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Robot Arm")
        ax.set_title(title)
        ax.invert_yaxis()
        ax.grid(axis="x", alpha=0.3)

        # Legend
        legend_patches = [
            mpatches.Patch(color=c, label=a) for a, c in color_map.items()
        ]
        legend_patches.append(mpatches.Patch(color="gray", alpha=0.4, label="failed"))
        ax.legend(handles=legend_patches, loc="upper right", fontsize=8)

        plt.tight_layout()
        if save_path:
            self._save_figure(fig, save_path)

    # ------------------------------------------------------------------
    # Resource utilisation timeline
    # ------------------------------------------------------------------

    def plot_resource_utilization(
        self,
        execution_log: ExecutionLog,
        save_path: Optional[str] = None,
        title: str = "Resource Utilization Over Time",
    ) -> None:
        """
        Plot the number of concurrently active arms over time.
        """
        if not execution_log.entries:
            logger.warning("Empty execution log; nothing to plot")
            return

        # Build event list: +1 at start, -1 at end
        events: List[tuple] = []
        for entry in execution_log.entries:
            events.append((entry.start_time, 1))
            events.append((entry.end_time, -1))
        events.sort()

        times: List[float] = []
        active_counts: List[int] = []
        current = 0
        for t, delta in events:
            times.append(t)
            current += delta
            active_counts.append(current)

        fig, ax = plt.subplots(figsize=(10, 4))
        self.fig = fig
        ax.fill_between(times, active_counts, step="post", alpha=0.4, color="#1f77b4")
        ax.step(times, active_counts, where="post", color="#1f77b4", linewidth=2)
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Active Arms")
        ax.set_title(title)
        ax.set_ylim(bottom=0)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        if save_path:
            self._save_figure(fig, save_path)

    # ------------------------------------------------------------------
    # Comparison bar chart
    # ------------------------------------------------------------------

    def plot_comparison(
        self,
        agent_metrics: EvaluationMetrics,
        baseline_metrics: EvaluationMetrics,
        save_path: Optional[str] = None,
        agent_label: str = "Agent",
        baseline_label: str = "Baseline",
        title: str = "Agent vs Baseline",
    ) -> None:
        """
        Side-by-side bar chart comparing agent and baseline on each metric.
        """
        metric_names = [
            "makespan",
            "task_success_rate",
            "resource_utilization",
            "constraint_violations",
        ]
        display_names = [
            "Makespan",
            "Success Rate",
            "Resource Util.",
            "Violations",
        ]

        agent_vals = [getattr(agent_metrics, m) for m in metric_names]
        baseline_vals = [getattr(baseline_metrics, m) for m in metric_names]

        x = list(range(len(metric_names)))
        width = 0.35

        fig, ax = plt.subplots(figsize=(10, 5))
        self.fig = fig

        bars1 = ax.bar([i - width / 2 for i in x], baseline_vals, width, label=baseline_label, color="#ff7f0e", alpha=0.85)
        bars2 = ax.bar([i + width / 2 for i in x], agent_vals, width, label=agent_label, color="#1f77b4", alpha=0.85)

        ax.set_xticks(x)
        ax.set_xticklabels(display_names)
        ax.set_ylabel("Value")
        ax.set_title(title)
        ax.legend()
        ax.grid(axis="y", alpha=0.3)

        # Annotate bars with values
        for bar in list(bars1) + list(bars2):
            height = bar.get_height()
            ax.annotate(
                f"{height:.2f}",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=7,
            )

        plt.tight_layout()
        if save_path:
            self._save_figure(fig, save_path)

    # ------------------------------------------------------------------
    # HTML report
    # ------------------------------------------------------------------

    def generate_html_report(
        self,
        results: Dict[str, Any],
        save_path: str,
        title: str = "Multi-Arm Scheduling Evaluation Report",
    ) -> None:
        """
        Generate a self-contained HTML report.

        *results* may contain any of the following keys:
        - ``metrics``: :class:`EvaluationMetrics`
        - ``execution_log``: :class:`ExecutionLog`
        - ``comparison``: dict with ``agent_metrics`` and ``baseline_metrics``
        - ``benchmark_result``: :class:`BenchmarkResult`
        """
        metrics: Optional[EvaluationMetrics] = results.get("metrics")
        execution_log: Optional[ExecutionLog] = results.get("execution_log")
        comparison = results.get("comparison")

        # Build embedded images
        gantt_img = ""
        util_img = ""
        comp_img = ""

        if execution_log and execution_log.entries:
            gantt_img = self._fig_to_base64_uri(self._make_gantt_figure(execution_log))
            util_img = self._fig_to_base64_uri(self._make_util_figure(execution_log))

        if comparison:
            am = comparison.get("agent_metrics", metrics)
            bm = comparison.get("baseline_metrics")
            if am and bm:
                comp_img = self._fig_to_base64_uri(self._make_comparison_figure(am, bm))

        # Build metrics table rows
        metrics_html = ""
        if metrics:
            rows = [
                ("Makespan", f"{metrics.makespan:.4f} s"),
                ("Task Success Rate", f"{metrics.task_success_rate * 100:.1f}%"),
                ("Resource Utilization", f"{metrics.resource_utilization * 100:.1f}%"),
                ("Constraint Violations", str(metrics.constraint_violations)),
                ("Total Tasks", str(metrics.total_tasks)),
                ("Completed Tasks", str(metrics.completed_tasks)),
                ("Failed Tasks", str(metrics.failed_tasks)),
            ]
            metrics_html = "\n".join(
                f"<tr><td>{name}</td><td>{val}</td></tr>" for name, val in rows
            )

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
  body {{ font-family: Arial, sans-serif; margin: 2em; background: #fafafa; }}
  h1 {{ color: #333; }}
  h2 {{ color: #555; margin-top: 2em; }}
  table {{ border-collapse: collapse; margin: 1em 0; }}
  th, td {{ border: 1px solid #ccc; padding: 8px 14px; text-align: left; }}
  th {{ background: #f0f0f0; }}
  .chart {{ text-align: center; margin: 1.5em 0; }}
  .chart img {{ max-width: 100%; border: 1px solid #ddd; border-radius: 4px; }}
</style>
</head>
<body>
<h1>{title}</h1>

{"<h2>Metrics Summary</h2><table><tr><th>Metric</th><th>Value</th></tr>" + metrics_html + "</table>" if metrics_html else ""}

{"<h2>Gantt Chart</h2><div class='chart'><img src='" + gantt_img + "' alt='Gantt Chart'></div>" if gantt_img else ""}

{"<h2>Resource Utilization</h2><div class='chart'><img src='" + util_img + "' alt='Resource Utilization'></div>" if util_img else ""}

{"<h2>Agent vs Baseline</h2><div class='chart'><img src='" + comp_img + "' alt='Comparison'></div>" if comp_img else ""}

</body>
</html>"""

        path = Path(save_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(html)
        logger.info("HTML report written to %s", save_path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _save_figure(self, fig: Figure, save_path: str) -> None:
        path = Path(save_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(str(path), dpi=150, bbox_inches="tight")
        plt.close(fig)
        logger.info("Figure saved to %s", save_path)

    def _fig_to_base64_uri(self, fig: Figure) -> str:
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        encoded = base64.b64encode(buf.read()).decode("ascii")
        return f"data:image/png;base64,{encoded}"

    def _make_gantt_figure(self, execution_log: ExecutionLog) -> Figure:
        arms: Dict[str, List[TaskEntry]] = {}
        for entry in execution_log.entries:
            arms.setdefault(entry.arm_id, []).append(entry)
        arm_ids = sorted(arms.keys())

        fig, ax = plt.subplots(figsize=(12, max(4, len(arm_ids) * 0.8)))

        for y_pos, arm_id in enumerate(arm_ids):
            entries = sorted(arms[arm_id], key=lambda e: e.start_time)
            color = _ARM_COLORS[y_pos % len(_ARM_COLORS)]
            for entry in entries:
                dur = entry.end_time - entry.start_time
                alpha = 1.0 if entry.status == "completed" else 0.4
                ax.barh(y_pos, dur, left=entry.start_time, height=0.6,
                        color=color, alpha=alpha, edgecolor="white", linewidth=0.5)
                ax.text(entry.start_time + dur / 2, y_pos, entry.task_id,
                        ha="center", va="center", fontsize=7, color="white")

        ax.set_yticks(range(len(arm_ids)))
        ax.set_yticklabels(arm_ids)
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Arm")
        ax.set_title("Gantt Chart")
        ax.invert_yaxis()
        ax.grid(axis="x", alpha=0.3)
        plt.tight_layout()
        return fig

    def _make_util_figure(self, execution_log: ExecutionLog) -> Figure:
        events: List[tuple] = []
        for e in execution_log.entries:
            events.append((e.start_time, 1))
            events.append((e.end_time, -1))
        events.sort()

        times: List[float] = []
        counts: List[int] = []
        cur = 0
        for t, d in events:
            times.append(t)
            cur += d
            counts.append(cur)

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.fill_between(times, counts, step="post", alpha=0.4, color="#1f77b4")
        ax.step(times, counts, where="post", color="#1f77b4", linewidth=2)
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Active Arms")
        ax.set_title("Resource Utilization")
        ax.set_ylim(bottom=0)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        return fig

    def _make_comparison_figure(
        self, agent: EvaluationMetrics, baseline: EvaluationMetrics
    ) -> Figure:
        names = ["Makespan", "Success Rate", "Resource Util.", "Violations"]
        agent_vals = [agent.makespan, agent.task_success_rate, agent.resource_utilization, float(agent.constraint_violations)]
        base_vals = [baseline.makespan, baseline.task_success_rate, baseline.resource_utilization, float(baseline.constraint_violations)]

        x = list(range(len(names)))
        width = 0.35
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.bar([i - width / 2 for i in x], base_vals, width, label="Baseline", color="#ff7f0e", alpha=0.85)
        ax.bar([i + width / 2 for i in x], agent_vals, width, label="Agent", color="#1f77b4", alpha=0.85)
        ax.set_xticks(x)
        ax.set_xticklabels(names)
        ax.set_ylabel("Value")
        ax.set_title("Agent vs Baseline")
        ax.legend()
        ax.grid(axis="y", alpha=0.3)
        plt.tight_layout()
        return fig
