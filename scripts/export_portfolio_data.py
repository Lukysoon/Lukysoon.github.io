"""
Extract visualization data from the AudioClassifier output HTML
and save as compact JSON for embedding in the portfolio page.
"""

import base64
import json
import struct
import sys
from pathlib import Path


def extract_traces(html_path: str) -> list[dict]:
    """Parse Plotly trace data from the output HTML file."""
    content = Path(html_path).read_text(encoding="utf-8")

    # Find the last Plotly.newPlot call (the actual data, not inside the library)
    idx = content.rfind("Plotly.newPlot(")
    if idx == -1:
        raise ValueError("No Plotly.newPlot() found in HTML")

    after = content[idx:]
    bracket_start = after.find('[{"customdata')
    if bracket_start == -1:
        bracket_start = after.find('[{"')

    decoder = json.JSONDecoder()
    traces, _ = decoder.raw_decode(after[bracket_start:])
    return traces


def decode_binary_array(data: dict) -> list[float]:
    """Decode Plotly binary float32 array to Python list."""
    raw = base64.b64decode(data["bdata"])
    n = len(raw) // 4
    values = struct.unpack(f"<{n}f", raw)
    return [round(v, 2) for v in values]


def main():
    project_root = Path(__file__).resolve().parent.parent
    html_path = project_root / "output" / "audio_classifier_3d.html"
    output_path = project_root / "portfolio_data.json"

    if not html_path.exists():
        print(f"Error: {html_path} not found. Run the pipeline first.")
        sys.exit(1)

    print(f"Reading {html_path}...")
    traces = extract_traces(str(html_path))

    result = {}
    total = 0

    for trace in traces:
        name = trace.get("name", "unknown")
        x_raw = trace.get("x", {})
        y_raw = trace.get("y", {})
        z_raw = trace.get("z", {})

        if isinstance(x_raw, dict) and "bdata" in x_raw:
            x = decode_binary_array(x_raw)
            y = decode_binary_array(y_raw)
            z = decode_binary_array(z_raw)
        elif isinstance(x_raw, list):
            x = [round(v, 2) for v in x_raw]
            y = [round(v, 2) for v in y_raw]
            z = [round(v, 2) for v in z_raw]
        else:
            print(f"  Skipping trace '{name}': unknown data format")
            continue

        result[name] = {"x": x, "y": y, "z": z}
        total += len(x)
        print(f"  {name}: {len(x)} points")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, separators=(",", ":"))

    size_kb = output_path.stat().st_size / 1024
    print(f"\nSaved {output_path} ({size_kb:.0f} KB, {total} points)")


if __name__ == "__main__":
    main()
