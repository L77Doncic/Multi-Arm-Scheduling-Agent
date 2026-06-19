#!/usr/bin/env python3
"""
Generate system architecture diagram using matplotlib.

Produces a publication-quality layered architecture diagram.
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np


def draw_architecture(save_path: str = "docs/source/assets/architecture.png"):
    """Draw the system architecture diagram."""
    fig, ax = plt.subplots(1, 1, figsize=(16, 12))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 12)
    ax.axis('off')
    ax.set_facecolor('#fafafa')
    fig.patch.set_facecolor('#fafafa')

    # Color scheme
    colors = {
        'agent': '#4A90D9',
        'harness': '#E8A838',
        'simulation': '#5CB85C',
        'evaluation': '#D9534F',
        'llm': '#9B59B6',
        'bg': '#F7F7F7',
        'text': '#2C3E50',
        'arrow': '#7F8C8D',
    }

    def draw_box(x, y, w, h, label, color, fontsize=11, alpha=0.9, sublabel=None):
        box = FancyBboxPatch((x, y), w, h,
                             boxstyle="round,pad=0.15",
                             facecolor=color, edgecolor='#34495E',
                             linewidth=1.5, alpha=alpha, zorder=2)
        ax.add_patch(box)
        if sublabel:
            ax.text(x + w/2, y + h/2 + 0.15, label,
                    ha='center', va='center', fontsize=fontsize,
                    fontweight='bold', color='white', zorder=3)
            ax.text(x + w/2, y + h/2 - 0.2, sublabel,
                    ha='center', va='center', fontsize=fontsize - 2,
                    color='white', alpha=0.85, zorder=3)
        else:
            ax.text(x + w/2, y + h/2, label,
                    ha='center', va='center', fontsize=fontsize,
                    fontweight='bold', color='white', zorder=3)

    def draw_arrow(x1, y1, x2, y2, label=None):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='->', color=colors['arrow'],
                                    lw=2, connectionstyle='arc3,rad=0'),
                    zorder=1)
        if label:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            ax.text(mx + 0.15, my, label, fontsize=8, color=colors['arrow'],
                    ha='left', va='center', style='italic', zorder=3)

    def draw_layer_bg(y, h, label, color):
        bg = FancyBboxPatch((0.5, y), 15, h,
                            boxstyle="round,pad=0.2",
                            facecolor=color, edgecolor='#BDC3C7',
                            linewidth=1, alpha=0.3, zorder=0)
        ax.add_patch(bg)
        ax.text(1.0, y + h - 0.25, label,
                fontsize=9, color='#7F8C8D', fontweight='bold',
                style='italic', zorder=1)

    # Title
    ax.text(8, 11.5, 'Multi-Arm Scheduling Agent — System Architecture',
            ha='center', va='center', fontsize=18, fontweight='bold',
            color=colors['text'], zorder=3)

    # Layer 1: User Interface
    draw_layer_bg(10.3, 0.8, 'User Interface', '#ECF0F1')
    draw_box(2, 10.4, 5, 0.6, 'NL Instruction', '#7F8C8D', fontsize=10)
    draw_box(9, 10.4, 5, 0.6, 'Scene Config (YAML)', '#7F8C8D', fontsize=10)

    # Layer 2: Agent Core
    draw_layer_bg(7.8, 2.2, 'Agent Core Layer', '#EBF5FB')
    draw_box(1.5, 8.2, 3.5, 1.2, 'TaskPlanner', colors['agent'],
             sublabel='NL → Task DAG')
    draw_box(6.25, 8.2, 3.5, 1.2, 'CodeGenerator', colors['agent'],
             sublabel='Primitives → Code')
    draw_box(11, 8.2, 3.5, 1.2, 'SchedulingAgent', colors['agent'],
             sublabel='Orchestrator')

    # LLM Clients (inside Agent Core)
    draw_box(3.5, 7.9, 2.2, 0.5, 'OpenAI', colors['llm'], fontsize=9)
    draw_box(6.0, 7.9, 2.2, 0.5, 'Anthropic', colors['llm'], fontsize=9)
    draw_box(8.5, 7.9, 2.2, 0.5, 'Heuristic', colors['llm'], fontsize=9)

    # Layer 3: Harness Framework
    draw_layer_bg(4.8, 2.7, 'Harness Engineering Framework', '#FEF9E7')
    draw_box(1.0, 5.2, 2.6, 1.0, 'TaskDecomposer', colors['harness'],
             sublabel='NL → Tasks')
    draw_box(4.0, 5.2, 2.6, 1.0, 'ResourceAllocator', colors['harness'],
             sublabel='Tasks → Arms')
    draw_box(7.0, 5.2, 2.6, 1.0, 'ResultValidator', colors['harness'],
             sublabel='Check Constraints')
    draw_box(10.0, 5.2, 2.6, 1.0, 'ExceptionHandler', colors['harness'],
             sublabel='Classify & Recover')
    draw_box(13.0, 5.2, 2.6, 1.0, 'FeedbackLoop', colors['harness'],
             sublabel='Adjust Strategy')

    # Layer 4: Simulation
    draw_layer_bg(2.5, 2.0, 'Simulation Layer', '#EAFAF1')
    draw_box(2.0, 2.8, 3.5, 1.2, 'MockSimulator', colors['simulation'],
             sublabel='Software Sim')
    draw_box(6.25, 2.8, 3.5, 1.2, 'IsaacSimInterface', colors['simulation'],
             sublabel='NVIDIA Physics')
    draw_box(10.5, 2.8, 3.5, 1.2, 'SceneBuilder', colors['simulation'],
             sublabel='Config → Scene')

    # Layer 5: Evaluation
    draw_layer_bg(0.3, 1.9, 'Evaluation Layer', '#FDEDEC')
    draw_box(1.5, 0.5, 3.5, 1.2, 'MetricsCalculator', colors['evaluation'],
             sublabel='Makespan/Util/Violations')
    draw_box(6.25, 0.5, 3.5, 1.2, 'BenchmarkRunner', colors['evaluation'],
             sublabel='MRTA-Benchmark')
    draw_box(11, 0.5, 3.5, 1.2, 'Visualizer', colors['evaluation'],
             sublabel='Gantt/Charts/HTML')

    # Arrows between layers
    # User → Agent
    draw_arrow(4.5, 10.4, 3.25, 9.4)
    draw_arrow(11.5, 10.4, 12.75, 9.4)

    # Agent internal flow
    draw_arrow(5.0, 8.8, 6.25, 8.8, 'tasks')
    draw_arrow(9.75, 8.8, 11.0, 8.8, 'code')

    # Agent → Harness
    draw_arrow(3.25, 8.2, 2.3, 6.2, 'decompose')
    draw_arrow(12.75, 8.2, 5.3, 6.2, 'allocate')
    draw_arrow(12.75, 8.2, 8.3, 6.2, 'validate')

    # Harness → Simulation
    draw_arrow(5.3, 5.2, 3.75, 4.0, 'execute')
    draw_arrow(8.3, 5.2, 8.0, 4.0, 'results')

    # Simulation → Harness feedback
    draw_arrow(3.75, 2.8, 11.3, 5.2, 'feedback')
    draw_arrow(8.0, 2.8, 14.3, 5.2, 'adjust')

    # Evaluation
    draw_arrow(3.75, 2.8, 3.25, 1.7, 'logs')
    draw_arrow(8.0, 2.8, 8.0, 1.7, 'benchmarks')

    # Legend
    legend_items = [
        mpatches.Patch(facecolor=colors['agent'], label='Agent Core'),
        mpatches.Patch(facecolor=colors['harness'], label='Harness Framework'),
        mpatches.Patch(facecolor=colors['simulation'], label='Simulation'),
        mpatches.Patch(facecolor=colors['evaluation'], label='Evaluation'),
        mpatches.Patch(facecolor=colors['llm'], label='LLM Clients'),
    ]
    ax.legend(handles=legend_items, loc='lower right', fontsize=9,
              framealpha=0.9, edgecolor='#BDC3C7')

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight',
                facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"Architecture diagram saved to {save_path}")


if __name__ == "__main__":
    import os
    os.makedirs("docs/source/assets", exist_ok=True)
    draw_architecture()
