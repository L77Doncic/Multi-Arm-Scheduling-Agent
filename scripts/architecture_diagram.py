#!/usr/bin/env python3
"""
Multi-Arm Scheduling Agent System — Publication-Quality Architecture Diagram
=============================================================================

Designed to match the visual conventions of top-tier CCF A conference papers
(NeurIPS, ICML, ICLR, CVPR, AAAI).

Design Principles (derived from analysis of accepted papers):
─────────────────────────────────────────────────────────────
1. COLOR PALETTE
   - Muted, colorblind-safe tones (Paul Tol / seaborn "muted" inspired)
   - Maximum 5 distinct hue families + 1 neutral (gray) for background/borders
   - Each architectural layer gets its own hue; saturation varies for sub-items
   - White text on saturated fills; near-black on light fills

2. TYPOGRAPHY
   - Serif family ("DejaVu Serif" or "Times New Roman") to match LaTeX body text
   - Consistent hierarchy: title 14pt bold, layer headers 11pt bold,
     component labels 9pt medium, annotations 8pt regular
   - ALL CAPS for layer headers only; Title Case for components

3. LAYOUT
   - Top-to-bottom flow (matches reading order; most ML system diagrams use this)
   - 5 horizontal layers separated by generous vertical spacing
   - Within each layer, components are centered and evenly spaced
   - Aspect ratio ≈ 1.4:1 (portrait) for single-column; 1:1.4 (landscape) for two-column

4. SHAPES & DECORATIONS
   - Rounded rectangles (FancyBboxPatch, boxstyle="round,pad=0.12")
   - Layer backgrounds: light tinted rectangles with subtle dashed borders
   - Component boxes: solid fills with 1px dark edge
   - "Our Contribution" components highlighted with thicker border + glow effect

5. ARROWS & DATA FLOW
   - Solid arrows: primary forward data flow (top → bottom)
   - Dashed arrows: feedback loops (bottom → top)
   - Arrow color: dark gray (#4A4A4A), not pure black (less harsh)
   - Arrow heads: filled triangular, size proportional to linewidth
   - Bundled/curved paths for parallel connections

6. COMPOSITION RULES
   - Figure size: (14, 10) inches for full-page; (7, 5) for single-column
   - DPI: 300 for PNG; vector PDF preferred
   - Margins: 0.5 inch all sides (bbox_inches='tight')
   - No axes, no grid, no frame — pure diagram
   - Legend placed bottom-right or bottom-center, compact horizontal layout

Dependencies:
    pip install matplotlib numpy
"""

import matplotlib
matplotlib.use('Agg')  # non-interactive backend for CI/server environments

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patheffects as pe
import numpy as np
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1: COLOR PALETTE
# ═══════════════════════════════════════════════════════════════════════════════
# Inspired by Paul Tol's "muted" and seaborn "muted" palettes
# All colors tested for WCAG AA contrast against white backgrounds

PALETTE = {
    # ── Layer background tints (very light, ~10% opacity of the main hue) ──
    'bg_layer1':    '#E8F0FE',   # light blue tint
    'bg_layer2':    '#FFF3E0',   # light orange tint
    'bg_layer3':    '#E8F5E9',   # light green tint
    'bg_layer4':    '#F3E5F5',   # light purple tint
    'bg_layer5':    '#FFF8E1',   # light amber tint

    # ── Layer 1 (User Interface) — Blue family ──
    'L1_main':      '#4C78A8',   # steel blue (primary)
    'L1_accent':    '#6BA3D6',   # lighter blue (secondary)
    'L1_text':      '#FFFFFF',   # white text on blue

    # ── Layer 2 (Agent Core) — Orange family ──
    'L2_main':      '#E07B39',   # burnt orange (primary)
    'L2_accent':    '#F5A623',   # golden amber (secondary)
    'L2_highlight': '#D4523E',   # warm red (for "Our Contribution")
    'L2_text':      '#FFFFFF',   # white text on orange

    # ── Layer 3 (Harness Framework) — Green family ──
    'L3_main':      '#54A65D',   # forest green (primary)
    'L3_accent':    '#7BC67F',   # sage green (secondary)
    'L3_text':      '#FFFFFF',   # white text on green

    # ── Layer 4 (Simulation) — Purple family ──
    'L4_main':      '#8C6BB1',   # medium purple (primary)
    'L4_accent':    '#B07CD8',   # lavender (secondary)
    'L4_text':      '#FFFFFF',   # white text on purple

    # ── Layer 5 (Evaluation) — Amber/Gold family ──
    'L5_main':      '#C49A22',   # dark gold (primary)
    'L5_accent':    '#E6C84D',   # bright gold (secondary)
    'L5_text':      '#FFFFFF',   # white text on gold

    # ── Neutral / Structural ──
    'arrow':        '#4A4A4A',   # dark gray for arrows (not pure black)
    'arrow_feedback':'#B0B0B0',  # lighter gray for feedback arrows
    'border':       '#333333',   # near-black for box edges
    'bg_canvas':    '#FAFAFA',   # off-white canvas background
    'legend_bg':    '#F5F5F5',   # legend background
    'text_dark':    '#1A1A1A',   # near-black for annotations
    'contribution': '#FF6B35',   # vivid orange for "our contribution" highlight
}

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2: TYPOGRAPHY
# ═══════════════════════════════════════════════════════════════════════════════

FONT = {
    'family':       'DejaVu Serif',    # matches LaTeX Computer Modern closely
    'title_size':   14,                 # main figure title
    'layer_size':   11,                 # layer header text
    'component_size': 9,               # component box labels
    'annotation_size': 8,              # small annotations, legend
    'weight_title': 'bold',
    'weight_layer': 'bold',
    'weight_component': 'semibold',
    'weight_annotation': 'normal',
}

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3: LAYOUT SPECIFICATIONS
# ═══════════════════════════════════════════════════════════════════════════════
# Coordinate system: origin (0,0) at bottom-left; x increases right, y increases up
# All values in inches (figure coordinates)

LAYOUT = {
    'fig_width':        14,      # inches
    'fig_height':       10,      # inches
    'dpi':              300,

    # Canvas margins (inches from figure edge)
    'margin_left':      0.8,
    'margin_right':     0.8,
    'margin_top':       1.0,     # extra space for title
    'margin_bottom':    1.2,     # space for legend

    # Layer dimensions (in figure-relative coordinates)
    'layer_x':          0.05,    # left edge of layer bg (fraction of fig width)
    'layer_width':      0.90,    # width of layer bg (fraction)
    'layer_height':     0.14,    # height of each layer bg (fraction)
    'layer_spacing':    0.015,   # vertical gap between layers (fraction)

    # Component box dimensions (absolute, in figure coordinates)
    'box_width':        1.8,     # inches
    'box_height':       0.55,    # inches
    'box_gap':          0.35,    # horizontal gap between boxes (inches)
    'box_corner_radius': 0.12,   # rounded corner radius (inches)

    # Arrow specifications
    'arrow_lw':         1.8,     # main flow arrows linewidth
    'arrow_head_width': 0.15,    # arrowhead width
    'arrow_head_length':0.10,    # arrowhead length
    'feedback_lw':      1.2,     # feedback arrow linewidth
    'feedback_style':   'dashed',# feedback line style
    'feedback_dash':    (5, 3),  # dash pattern (on, off) in points

    # Title position
    'title_y':          0.96,    # fraction from bottom
}

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4: ARCHITECTURE SPECIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

ARCHITECTURE = {
    'title': 'Multi-Arm Scheduling Agent System Architecture',

    'layers': [
        {
            'name': 'Layer 1: User Interface',
            'y_position': 0.82,       # y-center of this layer (fraction)
            'bg_color': PALETTE['bg_layer1'],
            'header_color': PALETTE['L1_main'],
            'components': [
                {'name': 'NL Instruction\nInput',      'width': 1.6},
                {'name': 'Scene Config\n(YAML)',       'width': 1.6},
            ],
            'box_color': PALETTE['L1_main'],
            'box_accent': PALETTE['L1_accent'],
            'text_color': PALETTE['L1_text'],
        },
        {
            'name': 'Layer 2: Agent Core',
            'y_position': 0.64,
            'bg_color': PALETTE['bg_layer2'],
            'header_color': PALETTE['L2_main'],
            'components': [
                {'name': 'TaskPlanner\nNL → Task DAG',   'width': 1.8, 'highlight': True},
                {'name': 'CodeGenerator\nPrimitives→Code', 'width': 1.8, 'highlight': True},
                {'name': 'SchedulingAgent\n(Orchestrator)', 'width': 1.8, 'highlight': True},
                {'name': 'LLM Clients\nOpenAI/Anthropic/\nHeuristic', 'width': 1.8},
            ],
            'box_color': PALETTE['L2_main'],
            'box_accent': PALETTE['L2_accent'],
            'text_color': PALETTE['L2_text'],
        },
        {
            'name': 'Layer 3: Harness Framework',
            'y_position': 0.46,
            'bg_color': PALETTE['bg_layer3'],
            'header_color': PALETTE['L3_main'],
            'components': [
                {'name': 'Task\nDecomposer',  'width': 1.5},
                {'name': 'Resource\nAllocator', 'width': 1.5},
                {'name': 'Result\nValidator',  'width': 1.5},
                {'name': 'Exception\nHandler', 'width': 1.5},
                {'name': 'Feedback\nLoop',     'width': 1.5},
            ],
            'box_color': PALETTE['L3_main'],
            'box_accent': PALETTE['L3_accent'],
            'text_color': PALETTE['L3_text'],
        },
        {
            'name': 'Layer 4: Simulation',
            'y_position': 0.28,
            'bg_color': PALETTE['bg_layer4'],
            'header_color': PALETTE['L4_main'],
            'components': [
                {'name': 'MockSimulator\n(Dev)',           'width': 2.0},
                {'name': 'IsaacSimInterface\n(Production,\nRTX GPU)', 'width': 2.0},
                {'name': 'SceneBuilder',                   'width': 1.6},
            ],
            'box_color': PALETTE['L4_main'],
            'box_accent': PALETTE['L4_accent'],
            'text_color': PALETTE['L4_text'],
        },
        {
            'name': 'Layer 5: Evaluation',
            'y_position': 0.10,
            'bg_color': PALETTE['bg_layer5'],
            'header_color': PALETTE['L5_main'],
            'components': [
                {'name': 'Metrics\nCalculator', 'width': 1.6},
                {'name': 'Benchmark\nRunner',    'width': 1.6},
                {'name': 'Visualizer',           'width': 1.6},
            ],
            'box_color': PALETTE['L5_main'],
            'box_accent': PALETTE['L5_accent'],
            'text_color': PALETTE['L5_text'],
        },
    ],

    # Data flow connections: (from_layer_idx, from_box_idx, to_layer_idx, to_box_idx, style)
    # style: 'forward' = solid, 'feedback' = dashed
    'connections': [
        # Layer 1 → Layer 2 (User Input → Agent Core)
        (0, 0, 1, 0, 'forward'),   # NL Input → TaskPlanner
        (0, 0, 1, 2, 'forward'),   # NL Input → SchedulingAgent
        (0, 1, 1, 2, 'forward'),   # Scene Config → SchedulingAgent

        # Layer 2 → Layer 3 (Agent Core → Harness)
        (1, 0, 2, 0, 'forward'),   # TaskPlanner → TaskDecomposer
        (1, 1, 2, 1, 'forward'),   # CodeGenerator → ResourceAllocator
        (1, 2, 2, 2, 'forward'),   # SchedulingAgent → ResultValidator
        (1, 2, 2, 3, 'forward'),   # SchedulingAgent → ExceptionHandler

        # Layer 3 → Layer 4 (Harness → Simulation)
        (2, 1, 3, 0, 'forward'),   # ResourceAllocator → MockSimulator
        (2, 1, 3, 1, 'forward'),   # ResourceAllocator → IsaacSimInterface
        (2, 0, 3, 2, 'forward'),   # TaskDecomposer → SceneBuilder

        # Layer 4 → Layer 5 (Simulation → Evaluation)
        (3, 0, 4, 0, 'forward'),   # MockSimulator → MetricsCalculator
        (3, 1, 4, 1, 'forward'),   # IsaacSimInterface → BenchmarkRunner
        (3, 2, 4, 2, 'forward'),   # SceneBuilder → Visualizer

        # Feedback Loop: Simulation → Harness (dashed)
        (3, 0, 2, 4, 'feedback'),  # MockSimulator → FeedbackLoop
        (3, 1, 2, 3, 'feedback'),  # IsaacSimInterface → ExceptionHandler
    ],

    # Feedback loop annotation
    'feedback_label': 'Feedback Loop',
}

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5: DRAWING FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def draw_rounded_rect(ax, x, y, w, h, color, edgecolor=None, lw=1.0,
                       alpha=1.0, corner_radius=0.12, zorder=1,
                       highlight=False, highlight_color=None):
    """Draw a rounded rectangle (FancyBboxPatch) with optional highlight glow."""
    if highlight and highlight_color:
        # Glow effect: larger, semi-transparent, slightly offset
        glow = FancyBboxPatch(
            (x - 0.04, y - 0.04), w + 0.08, h + 0.08,
            boxstyle=f"round,pad={corner_radius + 0.02}",
            facecolor=highlight_color,
            edgecolor='none',
            alpha=0.3,
            zorder=zorder - 1,
            transform=ax.transAxes,
        )
        ax.add_patch(glow)
        # Thicker border for highlighted boxes
        lw = 2.5
        edgecolor = highlight_color

    rect = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad={corner_radius}",
        facecolor=color,
        edgecolor=edgecolor or PALETTE['border'],
        linewidth=lw,
        alpha=alpha,
        zorder=zorder,
        transform=ax.transAxes,
    )
    ax.add_patch(rect)
    return rect


def draw_arrow_between_axes(ax, start_xy, end_xy, color=None, lw=1.8,
                             linestyle='-', dash_pattern=None, zorder=5,
                             connectionstyle='arc3,rad=0.0'):
    """Draw a FancyArrowPatch between two points in axes coordinates."""
    color = color or PALETTE['arrow']
    arrow = FancyArrowPatch(
        start_xy, end_xy,
        arrowstyle='->,head_width=0.15,head_length=0.10',
        color=color,
        linewidth=lw,
        linestyle=linestyle,
        connectionstyle=connectionstyle,
        zorder=zorder,
        transform=ax.transAxes,
        mutation_scale=15,
    )
    ax.add_patch(arrow)
    return arrow


def draw_layer_background(ax, layer_spec, layer_idx, total_layers):
    """Draw the light-colored background rectangle for a layer."""
    y_center = layer_spec['y_position']
    h = LAYOUT['layer_height']
    x = LAYOUT['layer_x']
    w = LAYOUT['layer_width']
    y = y_center - h / 2

    # Background rectangle
    draw_rounded_rect(
        ax, x, y, w, h,
        color=layer_spec['bg_color'],
        edgecolor=layer_spec['header_color'],
        lw=0.8,
        alpha=0.6,
        corner_radius=0.02,
        zorder=0,
    )

    # Layer header label (left-aligned, vertically centered)
    ax.text(
        x + 0.015, y_center,
        layer_spec['name'],
        ha='left', va='center',
        fontsize=FONT['layer_size'],
        fontweight=FONT['weight_layer'],
        fontfamily=FONT['family'],
        color=layer_spec['header_color'],
        transform=ax.transAxes,
        zorder=2,
    )


def draw_component_box(ax, x, y, w, h, label, box_color, text_color,
                        highlight=False, highlight_color=None):
    """Draw a single component box with label."""
    draw_rounded_rect(
        ax, x, y, w, h,
        color=box_color,
        edgecolor=PALETTE['border'],
        lw=1.2,
        alpha=0.92,
        corner_radius=LAYOUT['box_corner_radius'],
        zorder=3,
        highlight=highlight,
        highlight_color=highlight_color,
    )

    # Component label (centered in box)
    ax.text(
        x + w / 2, y + h / 2,
        label,
        ha='center', va='center',
        fontsize=FONT['component_size'],
        fontweight=FONT['weight_component'],
        fontfamily=FONT['family'],
        color=text_color,
        transform=ax.transAxes,
        zorder=4,
        linespacing=1.2,
    )


def compute_component_positions(layer_spec, fig_width):
    """Compute x-positions for component boxes within a layer, centered."""
    components = layer_spec['components']
    n = len(components)

    # Total width of all boxes + gaps
    total_box_width = sum(c['width'] for c in components)
    total_gap = (n - 1) * LAYOUT['box_gap']
    total_content_width = total_box_width + total_gap

    # Center within layer
    layer_left = LAYOUT['layer_x']
    layer_w = LAYOUT['layer_width']
    start_x = layer_left + (layer_w - total_content_width / fig_width) / 2

    positions = []
    current_x = start_x
    for comp in components:
        positions.append(current_x)
        current_x += (comp['width'] + LAYOUT['box_gap']) / fig_width

    return positions


def get_box_center(layer_spec, box_idx, fig_width):
    """Get the center (x, y) of a component box in axes coordinates."""
    positions = compute_component_positions(layer_spec, fig_width)
    comp = layer_spec['components'][box_idx]
    x_center = positions[box_idx] + comp['width'] / (2 * fig_width)
    y_center = layer_spec['y_position']
    return (x_center, y_center)


def get_box_edge(layer_spec, box_idx, fig_width, edge='top'):
    """Get the edge center of a component box for arrow connection."""
    cx, cy = get_box_center(layer_spec, box_idx, fig_width)
    comp = layer_spec['components'][box_idx]
    half_w = comp['width'] / (2 * fig_width)
    half_h = LAYOUT['box_height'] / 2

    if edge == 'top':
        return (cx, cy + half_h)
    elif edge == 'bottom':
        return (cx, cy - half_h)
    elif edge == 'left':
        return (cx - half_w, cy)
    elif edge == 'right':
        return (cx + half_w, cy)
    return (cx, cy)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6: MAIN DRAWING FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

def create_architecture_diagram(output_dir='.', formats=('pdf', 'png')):
    """
    Generate the complete Multi-Arm Scheduling Agent architecture diagram.

    Parameters
    ----------
    output_dir : str
        Directory to save output files.
    formats : tuple
        File formats to generate ('pdf', 'png', 'svg').

    Returns
    -------
    fig : matplotlib.figure.Figure
        The generated figure object.
    """
    fig_width = LAYOUT['fig_width']
    fig_height = LAYOUT['fig_height']

    fig, ax = plt.subplots(1, 1, figsize=(fig_width, fig_height))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    fig.patch.set_facecolor(PALETTE['bg_canvas'])
    ax.set_facecolor('none')

    layers = ARCHITECTURE['layers']

    # ── Draw layer backgrounds ──
    for idx, layer in enumerate(layers):
        draw_layer_background(ax, layer, idx, len(layers))

    # ── Draw component boxes ──
    # Store box positions for arrow drawing
    box_positions = {}  # (layer_idx, box_idx) -> (x_center, y_center)

    for layer_idx, layer in enumerate(layers):
        positions = compute_component_positions(layer, fig_width)
        y_center = layer['y_position']
        h = LAYOUT['box_height']

        for box_idx, comp in enumerate(layer['components']):
            x = positions[box_idx]
            y = y_center - h / 2
            w = comp['width'] / fig_width

            is_highlight = comp.get('highlight', False)

            draw_component_box(
                ax, x, y, w, h,
                label=comp['name'],
                box_color=layer['box_color'],
                text_color=layer['text_color'],
                highlight=is_highlight,
                highlight_color=PALETTE['contribution'] if is_highlight else None,
            )

            # Store center position
            box_positions[(layer_idx, box_idx)] = (
                x + w / 2, y_center
            )

    # ── Draw arrows (data flow connections) ──
    for conn in ARCHITECTURE['connections']:
        from_layer, from_box, to_layer, to_box, style = conn

        # Get edge points for arrow connection
        from_pos = get_box_edge(layers[from_layer], from_box, fig_width, edge='bottom')
        to_pos = get_box_edge(layers[to_layer], to_box, fig_width, edge='top')

        # Slight horizontal offset for better visual routing
        dx = to_pos[0] - from_pos[0]

        if style == 'feedback':
            # Feedback: curved path, dashed, lighter color
            # Route to the right side with a curve
            draw_arrow_between_axes(
                ax, from_pos, to_pos,
                color=PALETTE['arrow_feedback'],
                lw=LAYOUT['feedback_lw'],
                linestyle='--',
                connectionstyle='arc3,rad=-0.15',
                zorder=5,
            )
        else:
            # Forward flow: straight or slight curve
            curvature = 0.0
            if abs(dx) > 0.05:
                curvature = 0.1 * np.sign(dx)
            draw_arrow_between_axes(
                ax, from_pos, to_pos,
                color=PALETTE['arrow'],
                lw=LAYOUT['arrow_lw'],
                linestyle='-',
                connectionstyle=f'arc3,rad={curvature}',
                zorder=5,
            )

    # ── Draw feedback loop annotation ──
    # Place a label near the feedback arrows
    feedback_layer = layers[2]  # Harness layer
    feedback_pos = get_box_edge(feedback_layer, 4, fig_width, edge='right')
    ax.text(
        feedback_pos[0] + 0.08, feedback_pos[1] + 0.03,
        ARCHITECTURE['feedback_label'],
        ha='left', va='center',
        fontsize=FONT['annotation_size'],
        fontweight='bold',
        fontfamily=FONT['family'],
        color=PALETTE['arrow_feedback'],
        transform=ax.transAxes,
        zorder=6,
        style='italic',
        bbox=dict(
            boxstyle='round,pad=0.3',
            facecolor=PALETTE['bg_canvas'],
            edgecolor=PALETTE['arrow_feedback'],
            linewidth=0.8,
            alpha=0.9,
        ),
    )

    # ── Draw title ──
    ax.text(
        0.5, LAYOUT['title_y'],
        ARCHITECTURE['title'],
        ha='center', va='center',
        fontsize=FONT['title_size'],
        fontweight=FONT['weight_title'],
        fontfamily=FONT['family'],
        color=PALETTE['text_dark'],
        transform=ax.transAxes,
        zorder=10,
    )

    # ── Draw legend ──
    legend_elements = [
        mpatches.Patch(facecolor=PALETTE['L1_main'], edgecolor=PALETTE['border'],
                        label='User Interface'),
        mpatches.Patch(facecolor=PALETTE['L2_main'], edgecolor=PALETTE['border'],
                        label='Agent Core'),
        mpatches.Patch(facecolor=PALETTE['L3_main'], edgecolor=PALETTE['border'],
                        label='Harness Framework'),
        mpatches.Patch(facecolor=PALETTE['L4_main'], edgecolor=PALETTE['border'],
                        label='Simulation'),
        mpatches.Patch(facecolor=PALETTE['L5_main'], edgecolor=PALETTE['border'],
                        label='Evaluation'),
        mpatches.Patch(facecolor=PALETTE['contribution'], edgecolor=PALETTE['border'],
                        label='Our Contribution', alpha=0.8),
    ]

    # Add line style legend
    from matplotlib.lines import Line2D
    legend_elements.extend([
        Line2D([0], [0], color=PALETTE['arrow'], lw=LAYOUT['arrow_lw'],
               label='Forward Data Flow'),
        Line2D([0], [0], color=PALETTE['arrow_feedback'], lw=LAYOUT['feedback_lw'],
               linestyle='--', label='Feedback Loop'),
    ])

    legend = ax.legend(
        handles=legend_elements,
        loc='lower center',
        ncol=4,
        fontsize=FONT['annotation_size'],
        frameon=True,
        facecolor=PALETTE['legend_bg'],
        edgecolor=PALETTE['border'],
        framealpha=0.95,
        borderpad=0.8,
        labelspacing=0.4,
        columnspacing=1.2,
        handletextpad=0.5,
        bbox_to_anchor=(0.5, -0.02),
        prop={'family': FONT['family']},
    )

    # ── Save outputs ──
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    saved_files = []
    for fmt in formats:
        filepath = output_dir / f'architecture_diagram.{fmt}'
        fig.savefig(
            filepath,
            format=fmt,
            dpi=LAYOUT['dpi'],
            bbox_inches='tight',
            pad_inches=0.15,
            facecolor=fig.get_facecolor(),
            edgecolor='none',
            transparent=False,
        )
        saved_files.append(str(filepath))
        print(f"Saved: {filepath}")

    plt.close(fig)
    return fig, saved_files


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7: ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Generate Multi-Arm Scheduling Agent architecture diagram'
    )
    parser.add_argument(
        '--output-dir', '-o',
        default='.',
        help='Output directory for diagram files (default: current directory)'
    )
    parser.add_argument(
        '--format', '-f',
        nargs='+',
        default=['pdf', 'png'],
        choices=['pdf', 'png', 'svg'],
        help='Output formats (default: pdf png)'
    )
    parser.add_argument(
        '--dpi',
        type=int,
        default=300,
        help='DPI for raster output (default: 300)'
    )
    parser.add_argument(
        '--figsize',
        nargs=2,
        type=float,
        default=[14, 10],
        metavar=('WIDTH', 'HEIGHT'),
        help='Figure size in inches (default: 14 10)'
    )

    args = parser.parse_args()

    # Override layout with CLI args
    LAYOUT['dpi'] = args.dpi
    LAYOUT['fig_width'] = args.figsize[0]
    LAYOUT['fig_height'] = args.figsize[1]

    fig, files = create_architecture_diagram(
        output_dir=args.output_dir,
        formats=tuple(args.format),
    )

    print(f"\nGenerated {len(files)} file(s) in: {args.output_dir}")
    for f in files:
        print(f"  - {f}")
