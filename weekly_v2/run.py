"""Weekly bulletin v2 — personal decision edition, one command.

    python -m weekly_v2.run              # fetch, build HTML + PDF into personal_out/
    python -m weekly_v2.run --no-pdf     # HTML only
    python -m weekly_v2.run --open       # ...and open it in the browser
    python -m weekly_v2.run --from-cache path.json   # re-render a saved fetch (no network)

Runs on the owner's Mac: portfolio.yaml, rules.yaml, news.yaml and history/
are git-ignored and never leave the machine. No model is called; every
sentence is a rule over the numbers. The issue's "this week" rows are saved
to history/<cut>.json for next week's scorecard.

Quality gate: if the core series are missing, the page is still written for
inspection, history is not saved and the run exits non-zero.
"""
import json
import os
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from weekly_v2 import data as D, personal as P, render as R   # noqa: E402

CORE = ("ndx", "gold", "silver")
OUT = os.path.join(ROOT, "personal_out")


def html_to_pdf(html_path, pdf_path):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1160, "height": 1400})
        pg.goto("file://" + os.path.abspath(html_path))
        pg.wait_for_load_state("networkidle")
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(800)
        pg.emulate_media(media="print")
        pg.pdf(path=pdf_path, format="A4", print_background=True, scale=0.72,
               margin={"top": "8mm", "right": "6mm", "bottom": "8mm", "left": "6mm"})
        b.close()


def gate(data):
    missing = [k for k in CORE if k not in data["a"]]
    return [f"missing core series: {', '.join(missing)}"] if missing else []


def build(today=None, root=ROOT, cache=None):
    """Fetch everything and return the data dict the renderer takes."""
    portfolio, rules, news, example = P.load_inputs(root)
    if cache:
        with open(cache, encoding="utf-8") as fh:
            data = json.load(fh)
    else:
        today = today or date.today()
        extra = P.tickers(portfolio, rules)
        data, report, C, V = D.fetch(today, extra=extra)
        cut = data["cut"]
        data["personal"] = P.fetch_personal(portfolio, rules, C, V, cut, today, report)
        data["report_missing"] = sorted(set(report["missing"]))
        data["warnings"] = report["warnings"]
    data.update({"portfolio": portfolio, "rules": rules, "news": news, "example_files": example,
                 "prev_issue": P.previous_issue(data["cut"], root)})
    return data


def main(argv):
    cache = argv[argv.index("--from-cache") + 1] if "--from-cache" in argv else None
    print(f"Weekly v2 · personal · {date.today()}")
    data = build(cache=cache)
    print(f"  cut: {data['cut']} · series: {len(data['a'])} · example inputs: {data['example_files'] or 'none'}")
    os.makedirs(OUT, exist_ok=True)
    if not cache:
        with open(os.path.join(OUT, f"data_{data['cut']}.json"), "w") as fh:
            json.dump({k: v for k, v in data.items() if k not in ("portfolio", "rules", "news", "prev_issue", "example_files")}, fh)
    problems = gate(data)
    html, rows = R.render(data)
    path = os.path.join(OUT, f"karar_{data['cut']}.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"  ✅ {path}")
    if "--no-pdf" not in argv:
        try:
            html_to_pdf(path, path[:-5] + ".pdf")
            print(f"  ✅ {path[:-5]}.pdf")
        except Exception as e:
            print(f"  ⚠️  PDF failed: {e}")
    if problems:
        print(f"  ⛔ {'; '.join(problems)} — history not saved")
        return False
    if not data["example_files"]:
        P.save_issue(data["cut"], rows, ROOT)
        print(f"  history/{data['cut']}.json · {len(rows)} rows for next week's scorecard")
    else:
        print("  example inputs → history not saved")
    if "--open" in argv:
        os.system(f"open '{path}'")
    return True


if __name__ == "__main__":
    sys.exit(0 if main(sys.argv[1:]) else 1)
