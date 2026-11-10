"""python record.py live|video  -- drives the real UI. 'live' = first pass (fills cache), 'video' = records a cached replay."""
import sys, time, os
from playwright.sync_api import sync_playwright
mode = sys.argv[1]
secs = 100 if mode == "live" else 36
TURNS = ["Why is the sky blue?", "3 spiders, how many legs?", "Do dragons sleep?", "What's our home address?"]
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    kw = dict(viewport={"width": 1000, "height": 720})
    if mode == "video": kw.update(record_video_dir="demo/_tmp", record_video_size={"width": 1000, "height": 720})
    c = b.new_context(**kw); pg = c.new_page(); pg.on("dialog", lambda d: d.accept("2468"))
    pg.goto("http://127.0.0.1:8765/?secs=%d" % secs)
    # parent sets things (2 min, 5-7, animals/math/space)
    pg.click(".tab[data-t=parent]"); pg.wait_for_timeout(1500 if mode == "video" else 200)
    pg.fill("#s_min", "2"); pg.fill("#s_top", "animals, math, space"); pg.click("#s_save"); pg.wait_for_timeout(1200 if mode == "video" else 200)
    pg.click(".tab[data-t=kid]"); pg.wait_for_timeout(1000 if mode == "video" else 200)
    pg.type("#desc", "a purple dragon who loves math", delay=30 if mode == "video" else 0); pg.click("#mk"); pg.wait_for_timeout(1500 if mode == "video" else 200)
    for t in TURNS:
        pg.type("#txt", t, delay=25 if mode == "video" else 0); pg.press("#txt", "Enter")
        pg.wait_for_function("document.querySelectorAll('.bot').length>=%d" % (TURNS.index(t) + 1), timeout=60000)
        pg.wait_for_timeout(2200 if mode == "video" else 100)
    pg.wait_for_selector("#end", state="visible", timeout=120000); pg.wait_for_timeout(2500)
    pg.click(".tab[data-t=parent]"); pg.wait_for_timeout(4500 if mode == "video" else 3000)
    pg.click(".tab[data-t=proof]"); pg.wait_for_timeout(5000 if mode == "video" else 500)
    pg.screenshot(path="proof/proof_tab.png")
    c.close(); b.close()
if mode == "video":
    import glob, shutil
    f = glob.glob("demo/_tmp/*.webm")[0]; shutil.move(f, "demo/myfirstbuddy_demo.webm"); shutil.rmtree("demo/_tmp")
    print("video ok")
