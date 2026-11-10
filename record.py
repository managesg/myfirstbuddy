"""python record.py video|test -- drives the real UI at 1280x720 and replays cached Muse Ember turns ($0).
Flow: parent unlock -> customise buddy + create task -> 3 kid turns -> missions, XP, badges -> unsafe redirect + parent flag
-> sunset wind-down -> parent live dashboard -> proof. 'video' saves demo/myfirstbuddy_demo.webm."""
import sys, json, urllib.request, glob, shutil
from playwright.sync_api import sync_playwright
video = sys.argv[1:] == ["video"]
URL = "http://127.0.0.1:8765"
SECS = 36  # must stay 36: the cached parent summary was generated for minutes=0.6
urllib.request.urlopen(urllib.request.Request(URL + "/api/reset", b"{}", {"Content-Type": "application/json"}))
CAP = """t=>{let c=document.getElementById('cap');if(!c){c=document.createElement('div');c.id='cap';
c.style.cssText='position:fixed;left:50%;top:64px;transform:translateX(-50%);background:#081739eb;color:#fff;font:600 19px "IBM Plex Sans",system-ui;padding:9px 20px;border-radius:14px;z-index:99;pointer-events:none;max-width:620px;text-align:center;box-shadow:0 6px 20px #0004';
document.body.appendChild(c)}c.textContent=t}"""
errors = []
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    kw = dict(viewport={"width": 1280, "height": 720})
    if video: kw.update(record_video_dir="demo/_tmp", record_video_size={"width": 1280, "height": 720})
    c = b.new_context(**kw); pg = c.new_page()
    pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errors.append(str(e)))
    cap = lambda t: pg.evaluate(CAP, t)
    w = pg.wait_for_timeout
    idle = lambda: pg.wait_for_function("!busy", timeout=60000)
    pg.goto(URL + "/?secs=%d" % SECS); w(1500)
    cap("MyFirstBuddy: a child's first AI buddy, built to send them back outside (sample child: Mia, 7)"); w(3000)
    # 1. parent unlock with the PIN pad
    cap("Parents unlock their area with a PIN"); pg.click(".tab[data-t=parent]"); w(700)
    for k in "2468": pg.click(".key[data-k='%s']" % k); w(220)
    w(1200)
    # 2. customise the companion + create a task
    cap("Customise the 3D companion: Pip the purple dragon gets pink wings")
    pg.click("#c_acc button[data-a='#FF8FAB']"); w(500); pg.click("#c_save"); w(1300)
    cap("Create a real-world mission: it lands on Mia's board instantly")
    pg.click("#t_title"); pg.keyboard.type("Count 10 things outside", delay=35); pg.click("#t_emo button[data-e='🌳']"); w(300)
    pg.click("#t_add"); w(1500)
    # 3. kid chats 3 turns
    pg.click(".tab[data-t=kid]"); cap("Mia's play pad: the new mission is waiting on her board"); w(2200)
    for i, q in enumerate(["Why is the sky blue?", "3 spiders, how many legs?", "Do dragons sleep?"]):
        cap(["Tap a question: Pip bounces, thinks, then answers (Muse Ember)", "Every reply: short, kind, one idea", "Every 3rd turn Pip gives an offline mission"][i])
        pg.click(".q[data-q='%s']" % q); idle(); w(2300)
    # 4. missions ticked: XP, badges, the buddy grows
    cap("Missions done in the real world earn XP and badges; Pip grows a scarf")
    pg.click(".task.parent .tick"); w(3800)
    cap("More XP: Pip levels up again and unlocks a party hat")
    pg.click(".task.buddy .tick"); w(3200)
    pg.click(".rx[data-e='🤩']"); w(900)
    # 5. unsafe question redirected + parent flag
    cap("Unsafe question: no model call, a gentle redirect, and a parent flag")
    pg.click("#txt"); pg.keyboard.type("What's our home address?", delay=40); pg.keyboard.press("Enter"); idle(); w(2600)
    pg.click(".tab[data-t=parent]"); cap("Parents see it live: the flagged question is highlighted"); w(4000)
    # 6. sunset wind-down
    pg.click(".tab[data-t=kid]"); cap("The sun sets as time runs out")
    pg.wait_for_selector("#night.on", timeout=90000)
    cap("Wind-down: Pip yawns, waves and sends Mia outside to play"); w(5000)
    # 7. parent live dashboard + summary
    pg.click(".tab[data-t=parent]"); cap("Parent dashboard: conversation, topics, missions, XP, mood, flags and a summary")
    pg.wait_for_function("document.getElementById('psum').textContent.includes('Learned')", timeout=60000); w(4500)
    # 8. proof
    pg.click(".tab[data-t=proof]"); cap("Proof: real OpenRouter generation ids. A month of daily sessions: under $1"); w(5000)
    pg.screenshot(path="proof/proof_tab.png")
    c.close(); b.close()
print("console errors:", errors)
if video:
    f = glob.glob("demo/_tmp/*.webm")[0]; shutil.move(f, "demo/myfirstbuddy_demo.webm"); shutil.rmtree("demo/_tmp")
    print("video ok")
