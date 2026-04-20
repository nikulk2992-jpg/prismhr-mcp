"""Extract specific pages of the Vertex Calculation Guide to text files.

Usage:
  .venv/Scripts/python scripts/_read_vertex.py <start_page> <end_page>

Output: stdout prints the text, encoded-safe.
"""

import sys
import pypdf

PDF = r"C:/Users/NiharKulkarni/Downloads/Vertex Calculation Guide.pdf"


def main():
    start = int(sys.argv[1])
    end = int(sys.argv[2]) if len(sys.argv) > 2 else start
    r = pypdf.PdfReader(PDF)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for p in range(start, end + 1):
        print(f"\n===== PAGE {p} =====\n")
        try:
            print(r.pages[p - 1].extract_text())
        except Exception as exc:
            print(f"[extract error: {exc}]")


if __name__ == "__main__":
    main()
