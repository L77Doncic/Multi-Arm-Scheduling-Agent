#!/usr/bin/env python3
"""
Convert Markdown files in docs/ to PDF with academic paper styling.
Font sizes and layout follow typical academic paper conventions.
"""

import os
import sys
import glob
import markdown
from weasyprint import HTML

# Academic paper CSS styling
CSS = """
@page {
    size: A4;
    margin: 2.5cm 2.5cm 2.5cm 2.5cm;
    @bottom-center {
        content: counter(page);
        font-size: 10pt;
        color: #666;
    }
}

body {
    font-family: "Times New Roman", "SimSun", "Noto Serif CJK SC", serif;
    font-size: 12pt;
    line-height: 1.6;
    color: #333;
    text-align: justify;
}

h1 {
    font-size: 18pt;
    font-weight: bold;
    margin-top: 24pt;
    margin-bottom: 12pt;
    color: #1a1a1a;
    border-bottom: 2px solid #333;
    padding-bottom: 6pt;
}

h2 {
    font-size: 14pt;
    font-weight: bold;
    margin-top: 18pt;
    margin-bottom: 10pt;
    color: #222;
}

h3 {
    font-size: 12pt;
    font-weight: bold;
    margin-top: 14pt;
    margin-bottom: 8pt;
    color: #333;
}

h4 {
    font-size: 12pt;
    font-weight: bold;
    margin-top: 12pt;
    margin-bottom: 6pt;
    color: #444;
}

p {
    margin-bottom: 8pt;
    text-indent: 2em;
}

p:first-child, h1 + p, h2 + p, h3 + p, h4 + p {
    text-indent: 0;
}

ul, ol {
    margin-left: 2em;
    margin-bottom: 8pt;
}

li {
    margin-bottom: 4pt;
}

code {
    font-family: "Courier New", "Consolas", monospace;
    font-size: 10pt;
    background-color: #f4f4f4;
    padding: 1pt 4pt;
    border-radius: 3pt;
}

pre {
    background-color: #f8f8f8;
    border: 1px solid #ddd;
    border-radius: 4pt;
    padding: 10pt;
    margin: 10pt 0;
    overflow-x: auto;
}

pre code {
    background-color: transparent;
    padding: 0;
    font-size: 9pt;
    line-height: 1.4;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 12pt 0;
    font-size: 11pt;
}

th, td {
    border: 1px solid #ccc;
    padding: 6pt 10pt;
    text-align: left;
}

th {
    background-color: #f0f0f0;
    font-weight: bold;
}

tr:nth-child(even) {
    background-color: #f9f9f9;
}

blockquote {
    margin: 10pt 0;
    padding: 8pt 16pt;
    border-left: 3px solid #666;
    background-color: #fafafa;
    font-style: italic;
}

blockquote p {
    text-indent: 0;
    margin-bottom: 4pt;
}

strong {
    font-weight: bold;
}

em {
    font-style: italic;
}

a {
    color: #0066cc;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

hr {
    border: none;
    border-top: 1px solid #ccc;
    margin: 16pt 0;
}

img {
    max-width: 100%;
    height: auto;
}

.title-page {
    text-align: center;
    page-break-after: always;
}

.title-page h1 {
    font-size: 24pt;
    border-bottom: none;
    margin-top: 30%;
    margin-bottom: 20pt;
}

.title-page .subtitle {
    font-size: 14pt;
    color: #666;
    margin-bottom: 40pt;
}

.title-page .date {
    font-size: 12pt;
    color: #888;
}
"""


def convert_md_to_pdf(md_path, pdf_path, title=None):
    """Convert a single Markdown file to PDF."""
    with open(md_path, 'r', encoding='utf-8') as f:
        md_content = f.read()

    # Convert Markdown to HTML
    html_content = markdown.markdown(
        md_content,
        extensions=['tables', 'fenced_code', 'codehilite', 'toc', 'attr_list', 'md_in_html']
    )

    # Extract title from first H1 if not provided
    if title is None:
        import re
        title_match = re.search(r'^#\s+(.+)$', md_content, re.MULTILINE)
        if title_match:
            title = title_match.group(1)
        else:
            title = os.path.basename(md_path).replace('.md', '').replace('_', ' ').title()

    # Build full HTML document
    html_doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>{CSS}</style>
</head>
<body>
    {html_content}
</body>
</html>"""

    # Convert HTML to PDF
    HTML(string=html_doc).write_pdf(pdf_path)
    print(f"✓ {os.path.basename(md_path)} → {os.path.basename(pdf_path)}")


def main():
    docs_dir = os.path.join(os.path.dirname(__file__), '..', 'docs')
    docs_dir = os.path.abspath(docs_dir)

    if not os.path.exists(docs_dir):
        print(f"Error: docs directory not found at {docs_dir}")
        sys.exit(1)

    # Find all .md files
    md_files = sorted(glob.glob(os.path.join(docs_dir, '**', '*.md'), recursive=True))

    if not md_files:
        print("No .md files found in docs/")
        sys.exit(1)

    print(f"Found {len(md_files)} Markdown files to convert\n")

    # Create output directory
    output_dir = os.path.join(docs_dir, 'pdf')
    os.makedirs(output_dir, exist_ok=True)

    # Convert each file
    success_count = 0
    for md_path in md_files:
        # Preserve directory structure: docs/design/architecture.md → docs/pdf/design/architecture.pdf
        rel_path = os.path.relpath(md_path, docs_dir)
        pdf_rel = rel_path.replace('.md', '.pdf')
        pdf_path = os.path.join(output_dir, pdf_rel)
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

        try:
            convert_md_to_pdf(md_path, pdf_path)
            success_count += 1
        except Exception as e:
            print(f"✗ {os.path.basename(md_path)}: {e}")

    print(f"\nDone: {success_count}/{len(md_files)} files converted")
    print(f"Output directory: {output_dir}")


if __name__ == '__main__':
    main()
