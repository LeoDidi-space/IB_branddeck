#!/usr/bin/env python3
"""
Export Section 02 Logo Lockups from IB_brand_deck_13.html
Outputs 22 SVG files (+ optional PNGs) to ./exports/
"""

import os
import re

# ---------------------------------------------------------------------------
# Configuration: ordered (filename, bg_color) per lockup section
# ---------------------------------------------------------------------------

LOCKUP_MAP = {
    0: [  # Pattern 1 — Single Line Monogram
        ("p1_icon-only_light.svg",    None),
        ("p1_icon-wordmark_light.svg", None),
        ("p1_icon-fullname_light.svg", None),
        ("p1_icon-only_dark.svg",     "#1a2540"),
        ("p1_icon-wordmark_dark.svg", "#1a2540"),
        ("p1_icon-only_mono.svg",     "#EAE7E0"),
        ("p1_icon-jp_light.svg",      None),
        ("p1_icon-jp_dark.svg",       "#1a2540"),
    ],
    1: [  # Pattern 2 — Illuminate Rays
        ("p2_icon-wordmark_light.svg", None),
        ("p2_icon-only_light.svg",     None),
        ("p2_icon-wordmark_dark.svg",  "#1a2540"),
        ("p2_icon-only_dark.svg",      "#1a2540"),
        ("p2_icon-jp_light.svg",      None),
        ("p2_icon-jp_dark.svg",       "#1a2540"),
    ],
    2: [  # Pattern 3 — I&B Mark
        ("p3_icon-only_light.svg",     None),
        ("p3_wordmark-only_light.svg", None),
        ("p3_icon-fullname_light.svg", None),
        ("p3_icon-only_dark.svg",      "#1E3229"),
        ("p3_wordmark-only_dark.svg",  "#1E3229"),
        ("p3_icon-only_mono.svg",      "#EAE7E0"),
        ("p3_icon-jp_light.svg",       None),
        ("p3_icon-jp_dark.svg",        "#1E3229"),
    ],
}

SCALE = 2.0  # export width/height multiplier


# ---------------------------------------------------------------------------
# Extraction: regex-based to preserve original attribute casing
# ---------------------------------------------------------------------------

def extract_lockup_sections(html):
    """
    Returns list of sections, each a list of (svg_raw_str, lk_class_str).
    Uses regex to preserve original attribute casing (e.g. viewBox).
    """
    # Find each <section class="lockups-bg"> ... </section>
    section_pattern = re.compile(
        r'<section[^>]*class="[^"]*lockups-bg[^"]*"[^>]*>(.*?)</section>',
        re.DOTALL
    )
    # Find each <div class="lk ..."> ... </div> (non-greedy, handles nesting via counting)
    lk_open = re.compile(r'<div\s[^>]*class="([^"]*\blk\b[^"]*)"[^>]*>')

    sections = []
    for sec_m in section_pattern.finditer(html):
        sec_html = sec_m.group(1)
        lockups = []

        # Walk through all .lk divs in this section
        pos = 0
        while pos < len(sec_html):
            lk_m = lk_open.search(sec_html, pos)
            if not lk_m:
                break

            lk_class = lk_m.group(1)
            start = lk_m.start()
            inner_start = lk_m.end()

            # Find matching closing </div> by tracking depth
            depth = 1
            scan = inner_start
            while scan < len(sec_html) and depth > 0:
                next_open = sec_html.find('<div', scan)
                next_close = sec_html.find('</div>', scan)
                if next_close == -1:
                    break
                if next_open != -1 and next_open < next_close:
                    depth += 1
                    scan = next_open + 4
                else:
                    depth -= 1
                    if depth == 0:
                        lk_end = next_close + len('</div>')
                    scan = next_close + len('</div>')

            lk_html = sec_html[start:lk_end]

            # Extract SVG from within this lk div
            svg_m = re.search(r'(<svg\b.*?</svg>)', lk_html, re.DOTALL)
            if svg_m:
                lockups.append((svg_m.group(1), lk_class))

            pos = lk_end

        sections.append(lockups)

    return sections


# ---------------------------------------------------------------------------
# SVG processing
# ---------------------------------------------------------------------------

def parse_viewbox(svg_str):
    """Return (min_x, min_y, width, height) from viewBox attribute."""
    m = re.search(r'viewBox=["\']([^"\']+)["\']', svg_str, re.IGNORECASE)
    if not m:
        return None
    parts = m.group(1).replace(",", " ").split()
    if len(parts) == 4:
        return tuple(float(p) for p in parts)
    return None


def process_svg(svg_str, bg_color):
    """
    Prepare SVG for standalone export:
    - Remove inline style="width:...px"
    - Add explicit width/height at SCALE × viewBox dimensions
    - Ensure xmlns
    - Insert background rect for dark/mid variants
    """
    # Remove style attribute from opening <svg> tag only
    svg_str = re.sub(
        r'(<svg\b[^>]*?)\s+style="[^"]*"',
        r'\1',
        svg_str,
        count=1
    )

    # Ensure xmlns
    if 'xmlns=' not in svg_str:
        svg_str = re.sub(r'<svg\b', '<svg xmlns="http://www.w3.org/2000/svg"', svg_str, count=1)

    # Compute export dimensions from viewBox
    vb = parse_viewbox(svg_str)
    if vb:
        _, _, vbw, vbh = vb
        export_w = round(vbw * SCALE)
        export_h = round(vbh * SCALE)
    else:
        export_w, export_h = 200, 200

    # Remove any existing width/height attrs from opening svg tag
    svg_str = re.sub(r'(<svg\b[^>]*?)\s+width="[^"]*"', r'\1', svg_str, count=1)
    svg_str = re.sub(r'(<svg\b[^>]*?)\s+height="[^"]*"', r'\1', svg_str, count=1)

    # Inject width/height
    svg_str = re.sub(
        r'<svg\b',
        f'<svg width="{export_w}" height="{export_h}"',
        svg_str,
        count=1
    )

    # Insert background rect as first child if needed
    if bg_color:
        bg_rect = f'<rect width="100%" height="100%" fill="{bg_color}"/>'
        # Insert after the closing > of the opening <svg ...> tag
        close_pos = svg_str.index('>') + 1
        svg_str = svg_str[:close_pos] + bg_rect + svg_str[close_pos:]

    return svg_str


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(script_dir, "IB_brand_deck_13.html")
    exports_dir = os.path.join(script_dir, "exports")
    os.makedirs(exports_dir, exist_ok=True)

    print(f"Parsing: {html_path}")
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    sections = extract_lockup_sections(html)
    print(f"Found {len(sections)} lockup section(s)")

    exported = []
    failed = []

    for sec_idx, lockups in enumerate(sections):
        mapping = LOCKUP_MAP.get(sec_idx, [])
        print(f"\n--- Pattern {sec_idx + 1} ({len(lockups)} lockups found, {len(mapping)} expected) ---")

        for lk_idx, (svg_str, lk_class) in enumerate(lockups):
            if lk_idx >= len(mapping):
                print(f"  [{lk_idx}] SKIP (no mapping entry)")
                continue

            filename, bg = mapping[lk_idx]

            try:
                processed = process_svg(svg_str, bg)
                out_path = os.path.join(exports_dir, filename)
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(processed)

                # Quick verification: confirm viewBox preserved
                vb = parse_viewbox(processed)
                size_info = f"{round(vb[2]*SCALE)}×{round(vb[3]*SCALE)}px" if vb else "?"
                print(f"  [{lk_idx}] ✓  {filename}  ({size_info}, bg: {bg or 'transparent'})")
                exported.append(out_path)
            except Exception as e:
                print(f"  [{lk_idx}] ✗  {filename}  ERROR: {e}")
                failed.append(filename)

    print(f"\n{'='*50}")
    print(f"Exported {len(exported)} SVGs to: {exports_dir}")

    # Optional PNG export via cairosvg
    try:
        import cairosvg
        print("\nAttempting PNG export via cairosvg...")
        png_count = 0
        for svg_path in exported:
            png_path = svg_path.replace(".svg", ".png")
            try:
                cairosvg.svg2png(url=svg_path, write_to=png_path, scale=2.0)
                png_count += 1
            except Exception as e:
                print(f"  PNG failed for {os.path.basename(svg_path)}: {e}")
        print(f"Exported {png_count} PNGs")
    except ImportError:
        print("\nPNG export skipped — cairosvg not installed.")
        print("To enable PNG export: pip install cairosvg")

    if failed:
        print(f"\nFailed: {failed}")
    else:
        print("All exports successful.")


if __name__ == "__main__":
    main()
