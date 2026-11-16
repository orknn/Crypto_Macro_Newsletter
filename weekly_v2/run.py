"""Weekly bulletin v2 — one command, start to finish.

    python -m weekly_v2.run                 # build HTML + PDF, no email
    python -m weekly_v2.run --send-email    # ...and email confirmed subscribers
    TEST_TO=<address> python -m weekly_v2.run --send-email   # one test email only

Writes weekly_bulletin_{tr,en}.{html,pdf} (the names the workflow publishes)
and fetch_report.json. No model is called: every sentence is a rule over the
numbers, so a run costs nothing and cannot invent a figure.

Quality gate: if the three core assets are missing, or the newest close is
more than four days old, the files are still written for inspection but no
email goes out and the run exits non-zero.
"""
import json
import os
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from weekly_v2 import data as D, mail as M, render as R   # noqa: E402

CORE = ("ndx", "gold", "silver")
MAX_AGE_DAYS = 4


def archive_url(lang, today):
    y, w, _ = today.isocalendar()
    return f"https://nocashflow.net/bulletins/weekly/{y}-W{w:02d}.{lang}.html"


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


def gate(data, report, today):
    problems = [k for k in CORE if k not in data["a"]]
    if problems:
        return [f"missing core series: {', '.join(problems)}"]
    age = (today - date.fromisoformat(data["asof"])).days
    if age > MAX_AGE_DAYS:
        return [f"newest close is {age} days old ({data['asof']})"]
    return []


def main(argv):
    send = "--send-email" in argv
    today = date.today()
    print(f"Weekly v2 · {today}")
    data, report = D.fetch(today)
    print(f"  series: {len(data['a'])} · missing: {report['missing'] or 'none'}")
    for w in report["warnings"]:
        print(f"  ⚠️  {w}")
    problems = gate(data, report, today)
    report["gate"] = problems
    with open(os.path.join(ROOT, "fetch_report.json"), "w") as fh:
        json.dump({"edition": "weekly-v2", "asof": data["asof"], **report}, fh, indent=2)

    ok = not problems
    for lang in ("tr", "en"):
        url = archive_url(lang, today)
        html_path = os.path.join(ROOT, f"weekly_bulletin_{lang}.html")
        pdf_path = os.path.join(ROOT, f"weekly_bulletin_{lang}.pdf")
        with open(html_path, "w", encoding="utf-8") as fh:
            fh.write(R.render(data, lang, web_url=url))
        print(f"  ✅ {os.path.basename(html_path)}")
        try:
            html_to_pdf(html_path, pdf_path)
            print(f"  ✅ {os.path.basename(pdf_path)}")
        except Exception as e:
            print(f"  ⚠️  PDF failed ({e}); the email goes out without it.")
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
        if not send:
            continue
        if problems:
            print(f"  ⛔ email skipped ({lang}): {'; '.join(problems)}")
            continue
        from email_sender import send_to_subscribers
        t = R.teaser(data, lang)
        body = M.build(t, lang, url, data["today"])
        sent = send_to_subscribers(body, M.subject(t, lang), lang,
                                   pdf_path=pdf_path if os.path.exists(pdf_path) else None,
                                   from_addr="NO/CASHFLOW Weekly <dailyfinancialbulletin@nocashflow.net>",
                                   label="WEEKLY v2")
        ok = ok and bool(sent)
    if problems:
        print(f"::error title=Weekly v2 quality gate::{'; '.join(problems)}")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main(sys.argv[1:]) else 1)
