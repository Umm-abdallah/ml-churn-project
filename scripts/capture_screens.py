"""Captures d'écran automatiques de la pile complète (Swagger, Grafana, Kibana,
JMeter, docker compose ps). Lancé par .github/workflows/captures.yml après le
démarrage de la pile et les tirs JMeter.

Usage : python scripts/capture_screens.py <dossier_sortie>
"""
import html
import json
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "docs" / "captures")
OUT.mkdir(parents=True, exist_ok=True)
API = "http://localhost:8000"
GRAFANA = "http://localhost:3000"
KIBANA = "http://localhost:5601"
done, failed = [], []


def step(name):
    def wrap(fn):
        def run(*a, **k):
            try:
                fn(*a, **k)
                done.append(name)
                print(f"OK   {name}", flush=True)
            except Exception as exc:  # une capture ratée ne bloque pas les autres
                failed.append(f"{name}: {exc}")
                print(f"FAIL {name}: {exc}", flush=True)
        return run
    return wrap


def terminal_page(page, title, text, out):
    body = html.escape(text)
    page.set_content(
        "<html><body style='margin:0;background:#1e1e1e'>"
        f"<div style='background:#333;color:#eee;font:13px sans-serif;padding:7px 14px'>{html.escape(title)}</div>"
        "<pre style='margin:0;padding:16px 20px;color:#d4d4d4;font:13px/1.45 DejaVu Sans Mono,monospace'>"
        f"{body}</pre></body></html>")
    page.screenshot(path=str(OUT / out), full_page=True)


@step("17_docker_ps")
def docker_ps(page):
    ps = subprocess.run(["docker", "compose", "ps", "--format",
                         "table {{.Name}}\t{{.Service}}\t{{.Status}}\t{{.Ports}}"],
                        cwd=ROOT, capture_output=True, text=True).stdout
    terminal_page(page, "$ docker compose ps", ps, "17_docker_ps.png")


@step("03_swagger")
def swagger(page):
    page.goto(f"{API}/docs")
    page.wait_for_selector("#operations-default-predict_predict_post", timeout=30000)
    time.sleep(1)
    page.screenshot(path=str(OUT / "03_swagger.png"), full_page=True)


@step("05_swagger_predict")
def swagger_predict(page):
    page.goto(f"{API}/docs")
    block = page.locator("#operations-default-predict_predict_post")
    block.locator(".opblock-summary").click()
    page.get_by_role("button", name="Try it out").click()
    page.get_by_role("button", name="Execute").click()
    page.wait_for_selector(".live-responses-table .response-col_status", timeout=30000)
    time.sleep(1)
    block.screenshot(path=str(OUT / "05_swagger_predict.png"))


@step("10_grafana_dashboard")
def grafana(page):
    page.set_viewport_size({"width": 1920, "height": 1500})
    page.goto(f"{GRAFANA}/d/ml-churn-api/?orgId=1&from=now-15m&to=now&kiosk")
    page.wait_for_selector("[data-testid*='Panel header'], .react-grid-item", timeout=60000)
    time.sleep(12)  # laisser les requêtes Prometheus se terminer
    page.screenshot(path=str(OUT / "10_grafana_dashboard.png"), full_page=True)
    page.set_viewport_size({"width": 1600, "height": 1000})


def discover_url(query, columns):
    a = ("(columns:!(" + ",".join(columns) + "),"
         "dataSource:(dataViewId:ml-churn-logs,type:dataView),"
         "query:(language:kuery,query:'" + query.replace("'", "!'") + "'))")
    g = "(time:(from:now-1h,to:now))"
    return f"{KIBANA}/app/discover#/?_g={urllib.parse.quote(g)}&_a={urllib.parse.quote(a)}"


def kibana_shot(page, query, out, columns):
    page.goto(discover_url(query, columns))
    page.wait_for_load_state("networkidle", timeout=90000)
    time.sleep(8)
    for label in ("Dismiss", "Close tour", "Skip tour", "Got it", "Close"):
        try:
            page.get_by_role("button", name=label).first.click(timeout=1500)
        except Exception:
            pass
    page.keyboard.press("Escape")
    time.sleep(2)
    page.screenshot(path=str(OUT / out))


@step("11_kibana_discover")
def kibana_predictions(page):
    kibana_shot(page, 'event_type : "prediction"', "11_kibana_discover.png",
                ["prediction", "probability", "response_time_ms", "model_version", "request_id"])


@step("12_kibana_erreurs")
def kibana_errors(page):
    kibana_shot(page, 'level : "ERROR"', "12_kibana_erreurs.png",
                ["level", "message", "error", "request_id"])


def jmeter_shot(page, users, out):
    report = ROOT / "jmeter" / f"report-{users}u" / "index.html"
    page.goto(report.as_uri())
    page.wait_for_selector("#statisticsTable", timeout=30000)
    time.sleep(2)
    page.locator("#statisticsTable").scroll_into_view_if_needed()
    panel = page.locator("#statisticsTable").locator("xpath=ancestor::div[contains(@class,'panel')][1]")
    target = panel if panel.count() else page.locator("#statisticsTable")
    target.first.screenshot(path=str(OUT / out))


@step("13_jmeter_100u")
def jm100(page):
    jmeter_shot(page, 100, "13_jmeter_100u.png")


@step("14_jmeter_500u")
def jm500(page):
    jmeter_shot(page, 500, "14_jmeter_500u.png")


@step("15_jmeter_1000u")
def jm1000(page):
    jmeter_shot(page, 1000, "15_jmeter_1000u.png")


def jmeter_summary():
    rows = {}
    for users in (100, 500, 1000):
        stats = ROOT / "jmeter" / f"report-{users}u" / "statistics.json"
        if stats.exists():
            total = json.loads(stats.read_text())["Total"]
            rows[users] = {k: total[k] for k in (
                "sampleCount", "errorPct", "meanResTime", "medianResTime",
                "pct1ResTime", "pct2ResTime", "pct3ResTime", "maxResTime", "throughput")}
    (OUT / "jmeter_summary.json").write_text(json.dumps(rows, indent=2))


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1600, "height": 1000})
        for fn in (docker_ps, swagger, swagger_predict, grafana,
                   kibana_predictions, kibana_errors, jm100, jm500, jm1000):
            fn(page)
        browser.close()
    jmeter_summary()
    print("\nRéussies :", done)
    print("Échouées :", failed)


if __name__ == "__main__":
    main()
