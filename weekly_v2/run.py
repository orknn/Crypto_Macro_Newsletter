"""Weekly bulletin v2 — personal decision edition, one command.

    python -m weekly_v2.run              # fetch, build HTML + PDF into personal_out/
    python -m weekly_v2.run --no-pdf     # HTML only
    python -m weekly_v2.run --friday     # cut at the last Friday close instead of the latest close
    python -m weekly_v2.run --open       # ...and open it in the browser
    python -m weekly_v2.run --from-cache path.json   # re-render a saved fetch (no network)
    python -m weekly_v2.run --no-editor  # skip the model-written "editor's read" (gpt-6.1-sol, numbers checked)
    python -m weekly_v2.run --lang en    # English edition (karar_<cut>_en.html); --lang both = TR + EN

Runs on the owner's Mac: portfolio.yaml, rules.yaml, news.yaml and history/
are git-ignored and never leave the machine. Every number and condition is a
rule over the data; one model call (weekly_v2/editor.py) writes the short
"editor's read" on top from the finished page text, and it is printed only if
every number in it is on the page. Cash and total value are not sent. The issue's "this week" rows are saved
to history/<cut>.json for next week's scorecard.

Quality gate: if the core series are missing, the page is still written for
inspection, history is not saved and the run exits non-zero.
"""
import json
import os
import sys
from datetime import date, datetime

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


def build(today=None, root=ROOT, cache=None, friday=False):
    """Fetch everything and return the data dict the renderer takes."""
    portfolio, rules, news, example = P.load_inputs(root)
    if cache:
        with open(cache, encoding="utf-8") as fh:
            data = json.load(fh)
    else:
        today = today or date.today()
        extra = P.tickers(portfolio, rules)
        cut = D.last_friday(today, datetime.utcnow().hour) if friday else None
        data, report, C, V = D.fetch(today, extra=extra, cut=cut)
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
    data = build(cache=cache, friday="--friday" in argv)
    print(f"  cut: {data['cut']} · series: {len(data['a'])} · example inputs: {data['example_files'] or 'none'}")
    os.makedirs(OUT, exist_ok=True)
    if not cache:
        with open(os.path.join(OUT, f"data_{data['cut']}.json"), "w") as fh:
            json.dump({k: v for k, v in data.items() if k not in ("portfolio", "rules", "news", "prev_issue", "example_files")}, fh)
    problems = gate(data)
    lang = argv[argv.index("--lang") + 1] if "--lang" in argv else "tr"
    if "--no-editor" not in argv:
        from weekly_v2 import editor as E
        try:
            ed = E.write(R.render(data, lang="tr")[0], R.render(data, lang="en")[0])
            data["editor"] = ed
            cost = sum(u["usd"] for u in ed["usage"])
            print(f"  editor: {ed['model']} · {len(ed['usage'])} call(s) · ${cost:.4f} · "
                  + ("passed" if ed["tr"] else f"rejected {ed['rejected']}"))
            with open(os.path.join(OUT, f"editor_{data['cut']}.json"), "w", encoding="utf-8") as fh:
                json.dump(ed, fh, ensure_ascii=False, indent=1)
        except Exception as e:
            print(f"  ⚠️  editor failed, page goes out without it: {e}")
    langs = ("tr", "en") if lang == "both" else (lang,)
    paths, rows = [], []
    for lg in langs:
        html, r = R.render(data, lang=lg)
        rows = rows or r
        path = os.path.join(OUT, f"karar_{data['cut']}{'' if lg == 'tr' else '_' + lg}.html")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(html)
        paths.append(path)
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
        for path in paths:
            os.system(f"open '{path}'")
    return True


if __name__ == "__main__":
    sys.exit(0 if main(sys.argv[1:]) else 1)
