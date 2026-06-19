#!/usr/bin/env python3
"""
Publication-quality system architecture diagram.
Style: NeurIPS/ICLR paper figure — clean, minimal, professional.
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patheffects as pe
import numpy as np

# ── Color palette (muted academic) ──────────────────────────────
PALETTE = {
    'bg':         '#FAFBFC',
    'layer1':     '#EDF2F7',  # cool gray
    'layer2':     '#EBF8FF',  # light blue
    'layer3':     '#FFFFF0',  # warm ivory
    'layer4':     '#F0FFF4',  # light green
    'layer5':     '#FFF5F5',  # light rose
    'box1':       '#4A90D9',  # blue
    'box2':       '#D97706',  # amber
    'box3':       '#059669',  # emerald
    'box4':       '#DC2626',  # red
    'box5':       '#7C3AED',  # purple
    'llm':        '#6366F1',  # indigo
    'text':       '#1A202C',  # near-black
    'text_light': '#718096',  # gray
    'arrow':      '#A0AEC0',  # light gray
    'arrow_hi':   '#2D3748',  # dark gray
    'border':     '#CBD5E0',  # border gray
    'white':      '#FFFFFF',
}


def draw_box(ax, x, y, w, h, label, color, fontsize=9, sublabel=None,
             rounded=True, alpha=0.95, border_width=1.2):
    """Draw a rounded rectangle box with label."""
    style = "round,pad=0.08" if rounded else "square,pad=0"
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=style,
        facecolor=color,
        edgecolor=PALETTE['border'],
        linewidth=border_width,
        alpha=alpha,
        zorder=3,
    )
    ax.add_patch(box)

    # Text with white shadow for readability
    txt_color = PALETTE['white']
    if sublabel:
        ax.text(x + w/2, y + h/2 + 0.08, label,
                ha='center', va='center', fontsize=fontsize,
                fontweight='bold', color=txt_color, zorder=4,
                path_effects=[pe.withStroke(linewidth=2, foreground=color)])
        ax.text(x + w/2, y + h/2 - 0.12, sublabel,
                ha='center', va='center', fontsize=fontsize - 1.5,
                color=txt_color, alpha=0.85, zorder=4,
                path_effects=[pe.withStroke(linewidth=1.5, foreground=color)])
    else:
        ax.text(x + w/2, y + h/2, label,
                ha='center', va='center', fontsize=fontsize,
                fontweight='bold', color=txt_color, zorder=4,
                path_effects=[pe.withStroke(linewidth=2, foreground=color)])


def draw_layer(ax, y, h, label, bg_color, label_color):
    """Draw a layer background band with label."""
    bg = FancyBboxPatch(
        (0.3, y), 15.4, h,
        boxstyle="round,pad=0.12",
        facecolor=bg_color,
        edgecolor=PALETTE['border'],
        linewidth=0.8,
        alpha=0.6,
        zorder=0,
    )
    ax.add_patch(bg)
    # Layer label (rotated, on the left)
    ax.text(0.6, y + h/2, label,
            ha='left', va='center', fontsize=8,
            fontweight='bold', color=label_color,
            rotation=90, zorder=1, alpha=0.7)


def draw_arrow(ax, x1, y1, x2, y2, color=None, style='->', lw=1.5, label=None):
    """Draw an arrow between two points."""
    c = color or PALETTE['arrow']
    ax.annotate(
        '', xy=(x2, y2), xytext=(x1, y1),
        arrowprops=dict(
            arrowstyle=style,
            color=c,
            lw=lw,
            connectionstyle='arc3,rad=0',
            shrinkA=2, shrinkB=2,
        ),
        zorder=2,
    )
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(mx + 0.1, my, label,
                fontsize=6.5, color=c, ha='left', va='center',
                style='italic', zorder=3, alpha=0.8)


def draw_curved_arrow(ax, x1, y1, x2, y2, color=None, rad=0.3, label=None):
    """Draw a curved arrow."""
    c = color or PALETTE['arrow_hi']
    ax.annotate(
        '', xy=(x2, y2), xytext=(x1, y1),
        arrowprops=dict(
            arrowstyle='->',
            color=c,
            lw=1.8,
            connectionstyle=f'arc3,rad={rad}',
            shrinkA=3, shrinkB=3,
        ),
        zorder=2,
    )
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        offset = 0.3 if rad > 0 else -0.3
        ax.text(mx + offset, my + 0.15, label,
                fontsize=6.5, color=c, ha='center', va='center',
                style='italic', zorder=3, alpha=0.8)


def draw_architecture(save_path="docs/source/assets/architecture.png"):
    fig, ax = plt.subplots(figsize=(14, 10), dpi=150)
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 11.5)
    ax.axis('off')
    fig.patch.set_facecolor(PALETTE['bg'])
    ax.set_facecolor(PALETTE['bg'])

    # ── Title ────────────────────────────────────────────────────
    ax.text(8, 11.1, 'Multi-Arm Scheduling Agent',
            ha='center', va='center', fontsize=16, fontweight='700',
            color=PALETTE['text'], zorder=5)
    ax.text(8, 10.75, 'LLM-Driven Industrial Robot Scheduling with Harness Engineering',
            ha='center', va='center', fontsize=9, color=PALETTE['text_light'],
            zorder=5)

    # ── Layer 5: Evaluation (bottom) ─────────────────────────────
    draw_layer(ax, 0.3, 1.8, 'Evaluation', PALETTE['layer5'], PALETTE['box4'])
    draw_box(ax, 1.2, 0.5, 3.2, 1.1, 'Metrics\nCalculator', PALETTE['box4'],
             fontsize=8.5, sublabel='Makespan · Util · Violations')
    draw_box(ax, 5.4, 0.5, 3.2, 1.1, 'Benchmark\nRunner', PALETTE['box4'],
             fontsize=8.5, sublabel='MRTA-Benchmark')
    draw_box(ax, 9.6, 0.5, 3.2, 1.1, 'Visualizer', PALETTE['box4'],
             fontsize=8.5, sublabel='Gantt · Charts · HTML')

    # ── Layer 4: Simulation ──────────────────────────────────────
    draw_layer(ax, 2.3, 1.8, 'Simulation', PALETTE['layer4'], PALETTE['box3'])
    draw_box(ax, 1.2, 2.5, 3.2, 1.1, 'Mock\nSimulator', PALETTE['box3'],
             fontsize=8.5, sublabel='CPU · Dev/Test')
    draw_box(ax, 5.4, 2.5, 3.2, 1.1, 'Isaac Sim\nInterface', PALETTE['box3'],
             fontsize=8.5, sublabel='RTX GPU · Physics')
    draw_box(ax, 9.6, 2.5, 3.2, 1.1, 'Scene\nBuilder', PALETTE['box3'],
             fontsize=8.5, sublabel='Config → Scene')

    # ── Layer 3: Harness Framework ───────────────────────────────
    draw_layer(ax, 4.3, 1.8, 'Harness', PALETTE['layer3'], PALETTE['box2'])
    draw_box(ax, 0.6, 4.5, 2.4, 1.1, 'Task\nDecomposer', PALETTE['box2'],
             fontsize=8, sublabel='NL → Tasks')
    draw_box(ax, 3.3, 4.5, 2.4, 1.1, 'Resource\nAllocator', PALETTE['box2'],
             fontsize=8, sublabel='Tasks → Arms')
    draw_box(ax, 6.0, 4.5, 2.4, 1.1, 'Result\nValidator', PALETTE['box2'],
             fontsize=8, sublabel='Constraints')
    draw_box(ax, 8.7, 4.5, 2.4, 1.1, 'Exception\nHandler', PALETTE['box2'],
             fontsize=8, sublabel='Recovery')
    draw_box(ax, 11.4, 4.5, 2.4, 1.1, 'Feedback\nLoop', PALETTE['box2'],
             fontsize=8, sublabel='Adjust Strategy')

    # ── Layer 2: Agent Core ──────────────────────────────────────
    draw_layer(ax, 6.3, 2.5, 'Agent Core', PALETTE['layer2'], PALETTE['box1'])
    draw_box(ax, 1.0, 7.2, 3.0, 1.2, 'Task\nPlanner', PALETTE['box1'],
             fontsize=9, sublabel='NL → Task DAG')
    draw_box(ax, 5.5, 7.2, 3.0, 1.2, 'Code\nGenerator', PALETTE['box1'],
             fontsize=9, sublabel='Primitives → Code')
    draw_box(ax, 10.0, 7.2, 3.0, 1.2, 'Scheduling\nAgent', PALETTE['box1'],
             fontsize=9, sublabel='Orchestrator')

    # LLM Clients (sub-row)
    draw_box(ax, 2.5, 6.5, 2.0, 0.5, 'OpenAI', PALETTE['llm'], fontsize=7.5)
    draw_box(ax, 4.8, 6.5, 2.0, 0.5, 'Anthropic', PALETTE['llm'], fontsize=7.5)
    draw_box(ax, 7.1, 6.5, 2.0, 0.5, 'Heuristic', PALETTE['llm'], fontsize=7.5)

    # ── Layer 1: User Interface (top) ────────────────────────────
    draw_layer(ax, 9.0, 1.3, 'Input', PALETTE['layer1'], PALETTE['text_light'])
    draw_box(ax, 2.0, 9.2, 4.5, 0.8, 'Natural Language Instruction', '#718096',
             fontsize=9, rounded=True)
    draw_box(ax, 8.0, 9.2, 4.5, 0.8, 'Scene Configuration (YAML)', '#718096',
             fontsize=9, rounded=True)

    # ── Arrows: User → Agent ─────────────────────────────────────
    draw_arrow(ax, 4.25, 9.2, 2.5, 8.4, lw=1.8)
    draw_arrow(ax, 10.25, 9.2, 11.5, 8.4, lw=1.8)

    # ── Arrows: Agent internal flow ──────────────────────────────
    draw_arrow(ax, 4.0, 7.8, 5.5, 7.8, label='tasks', lw=1.5)
    draw_arrow(ax, 8.5, 7.8, 10.0, 7.8, label='code', lw=1.5)

    # ── Arrows: Agent → Harness ──────────────────────────────────
    draw_arrow(ax, 2.5, 7.2, 1.8, 5.6, lw=1.3)
    draw_arrow(ax, 7.0, 7.2, 4.5, 5.6, lw=1.3)
    draw_arrow(ax, 11.5, 7.2, 7.2, 5.6, lw=1.3)

    # ── Arrows: Harness → Simulation ─────────────────────────────
    draw_arrow(ax, 4.5, 4.5, 2.8, 3.6, lw=1.3)
    draw_arrow(ax, 7.2, 4.5, 7.0, 3.6, lw=1.3)

    # ── Arrows: Simulation → Evaluation ──────────────────────────
    draw_arrow(ax, 2.8, 2.5, 2.8, 1.6, lw=1.2)
    draw_arrow(ax, 7.0, 2.5, 7.0, 1.6, lw=1.2)

    # ── Curved Arrow: Feedback Loop (Simulation → Harness) ───────
    draw_curved_arrow(ax, 2.8, 2.5, 12.6, 4.5, rad=0.4,
                      color='#E53E3E', label='feedback')

    # ── Legend ────────────────────────────────────────────────────
    legend_x, legend_y = 13.2, 8.5
    legend_items = [
        ('Agent Core', PALETTE['box1']),
        ('Harness', PALETTE['box2']),
        ('Simulation', PALETTE['box3']),
        ('Evaluation', PALETTE['box4']),
        ('LLM Client', PALETTE['llm']),
    ]
    for i, (name, color) in enumerate(legend_items):
        ly = legend_y - i * 0.35
        rect = FancyBboxPatch((legend_x, ly), 0.3, 0.25,
                              boxstyle="round,pad=0.02",
                              facecolor=color, edgecolor='none',
                              alpha=0.9, zorder=4)
        ax.add_patch(rect)
        ax.text(legend_x + 0.4, ly + 0.12, name,
                fontsize=7, color=PALETTE['text'], va='center', zorder=4)

    # ── Feedback arrow label ─────────────────────────────────────
    ax.text(8.0, 1.8, 'Closed-Loop Feedback',
            ha='center', va='center', fontsize=7, color='#E53E3E',
            fontweight='bold', style='italic', zorder=4, alpha=0.8)

    plt.tight_layout(pad=0.5)
    plt.savefig(save_path, dpi=150, bbox_inches='tight',
                facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"Saved: {save_path}")


if __name__ == "__main__":
    import os
    os.makedirs("docs/source/assets", exist_ok=True)
    draw_architecture()
