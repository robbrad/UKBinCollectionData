# DIAGNOSTIC ONLY - never merge. Fetches arbitrary URLs from CI and prints
# stripped bodies, for investigating council sites unreachable from a sandbox.
import json
import re
import sys
import time

import requests

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
)
BODY_MAX = 60000


def strip(html):
    html = html or ""
    i = html.lower().find("<body")
    html = html[i:] if i >= 0 else html
    html = re.sub(r"<(style|svg|noscript)\b.*?</\1>", "", html, flags=re.S | re.I)
    html = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    return re.sub(r"\s+", " ", html)[:BODY_MAX]


def via_requests(p):
    s = requests.Session()
    s.headers.update({"User-Agent": UA, **p.get("headers", {})})
    kw = {"timeout": 30, "allow_redirects": True}
    if p.get("json") is not None:
        kw["json"] = p["json"]
    if p.get("data") is not None:
        kw["data"] = p["data"]
    r = s.request(p.get("method", "GET"), p["url"], **kw)
    hops = " -> ".join(f"{h.status_code} {h.url}" for h in r.history)
    print(f"status={r.status_code} final={r.url} hops=[{hops}] ct={r.headers.get('Content-Type')}")
    body = r.text if p.get("raw") else strip(r.text)
    print(body[:BODY_MAX])


def via_selenium(p):
    from selenium import webdriver

    opts = webdriver.ChromeOptions()
    opts.add_argument("--headless=new")
    opts.add_argument(f"--user-agent={UA}")
    d = webdriver.Remote(command_executor="http://localhost:4444", options=opts)
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import Select

    def dump(label):
        print(f"--- {label}: final={d.current_url} title={d.title!r}")
        src = d.page_source
        if not p.get("scripts"):
            src = re.sub(r"<script\b.*?</script>", "", src, flags=re.S | re.I)
        print(strip(src))

    try:
        d.get(p["url"])
        time.sleep(p.get("wait", 8))
        for step in p.get("steps", []):
            try:
                if "type" in step:
                    el = d.find_element(By.CSS_SELECTOR, step["type"][0])
                    el.clear()
                    el.send_keys(step["type"][1])
                elif "click" in step:
                    d.execute_script("arguments[0].click();", d.find_element(By.CSS_SELECTOR, step["click"]))
                elif "click_xpath" in step:
                    d.execute_script("arguments[0].click();", d.find_element(By.XPATH, step["click_xpath"]))
                elif "select_contains" in step:
                    sel = Select(d.find_element(By.CSS_SELECTOR, step["select_contains"][0]))
                    match = [o for o in sel.options if step["select_contains"][1] in o.text]
                    print(f"options: {[(o.get_attribute('value'), o.text) for o in sel.options][:30]}")
                    sel.select_by_visible_text(match[0].text)
                elif "sleep" in step:
                    time.sleep(step["sleep"])
                elif "dump" in step:
                    dump(step["dump"])
            except Exception as e:
                print(f"STEP {step} FAILED {e!r}"[:600])
        dump("end")
    finally:
        d.quit()


for p in json.load(open(sys.argv[1])):
    print(f"\n### PROBE {p['name']} {p.get('method', 'GET')} {p['url']}")
    try:
        (via_selenium if p.get("selenium") else via_requests)(p)
    except Exception as e:
        print(f"ERROR {e!r}"[:1500])
    sys.stdout.flush()
