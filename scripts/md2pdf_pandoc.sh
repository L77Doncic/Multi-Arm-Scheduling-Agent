#!/bin/bash
# Convert academic markdown docs to PDF using pandoc + xelatex
# Font sizes follow Chinese academic paper conventions

DOCS_DIR="$(dirname "$0")/../docs"
PDF_DIR="$DOCS_DIR/pdf"
mkdir -p "$PDF_DIR"

convert() {
    local input="$1"
    local output="$2"
    local title="$3"
    echo "Converting: $(basename "$input") → $(basename "$output")"
    pandoc "$input" \
        -o "$output" \
        --pdf-engine=xelatex \
        -V mainfont="Liberation Serif" \
        -V CJKmainfont="Noto Serif CJK SC" \
        -V sansfont="Noto Sans CJK SC" \
        -V monofont="Noto Sans Mono CJK SC" \
        -V geometry:margin=2.5cm \
        -V fontsize=12pt \
        -V papersize=a4 \
        -V documentclass=article \
        -V linestretch=2.0 \
        -V colorlinks=true \
        -V linkcolor=blue \
        -V urlcolor=blue \
        --highlight-style=tango \
        -V header-includes='\pagestyle{plain}\setlength{\parindent}{2em}\usepackage{titlesec}\titleformat{\section}{\Large\bfseries}{}{0em}{}\titleformat{\subsection}{\large\bfseries}{}{0em}{}\titleformat{\subsubsection}{\normalsize\bfseries}{}{0em}{}' \
        --toc \
        --toc-depth=3 \
        2>&1
    if [ $? -eq 0 ]; then
        echo "  ✓ Done: $(ls -lh "$output" | awk '{print $5}')"
    else
        echo "  ✗ Failed"
    fi
}

convert \
    "$DOCS_DIR/design/harness_design.md" \
    "$PDF_DIR/harness_design.pdf" \
    "Harness Engineering 框架设计文档"

convert \
    "$DOCS_DIR/testing/simulation_report.md" \
    "$PDF_DIR/simulation_report.pdf" \
    "仿真测试报告"

convert \
    "$DOCS_DIR/evaluation/benchmark_report.md" \
    "$PDF_DIR/benchmark_report.pdf" \
    "评估对比结果报告"

echo ""
echo "All PDFs generated in: $PDF_DIR"
ls -lh "$PDF_DIR"/*.pdf 2>/dev/null
