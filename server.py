"""MyFirstBuddy prototype server. stdlib only. SAMPLE DATA only (Mia, 7 / Pip)."""
import json, os, re, sys, time, hashlib, subprocess, secrets, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
R = os.path.dirname(os.path.abspath(__file__))
P = lambda *a: os.path.join(R, *a)
MODEL = "meta/muse-ember"
CAP = 0.40  # hard cap on NEW spend
UNSAFE = re.compile(r"address|phone|where do you live|password|kill|gun|sex|secret|hurt", re.I)
REDIRECT = "I can't help with that one, Mia. Let's ask a grown-up together! Want to hear about space or animals instead?"

def key():
    k = os.environ.get("OPENROUTER_API_KEY")
    if not k:
        k = subprocess.run(["powershell", "-NoProfile", "-Command",
            "[Environment]::GetEnvironmentVariable('OPENROUTER_API_KEY','User')"], capture_output=True, text=True).stdout.strip()
    return k

def rj(path, d):
    try: return json.load(open(P(path), encoding="utf-8"))
    except Exception: return d
def wj(path, o): json.dump(o, open(P(path), "w", encoding="utf-8"), indent=1)

TOKENS = set()
def pin_hash(salt, pin): return hashlib.sha256((salt + pin).encode()).hexdigest()
def ensure_pin(pin="2468"):  # sample PIN, documented in README; shortcut: no attempt rate-limit
    s = rj("data/settings.json", {})
    if "pin_hash" not in s:
        s["pin_salt"] = secrets.token_hex(8); s["pin_hash"] = pin_hash(s["pin_salt"], pin); wj("data/settings.json", s)

def spent():
    t = 0.0
    try:
        for l in open(P("proof", "openrouter_log.jsonl"), encoding="utf-8"):
            t += float(json.loads(l).get("cost") or 0)
    except FileNotFoundError: pass
    return t

def logline(o):
    with open(P("proof", "openrouter_log.jsonl"), "a", encoding="utf-8") as f: f.write(json.dumps(o) + "\n")

def guard(total=None):
    total = spent() if total is None else total
    if total >= CAP or 0.11 + total >= 0.95: raise RuntimeError("budget guard tripped: $%.4f" % total)

def parse(txt):
    t = re.sub(r"^```(?:json)?|```$", "", txt.strip(), flags=re.M).strip()
    try: return json.loads(t)
    except Exception:
        m = re.search(r'"reply"\s*:\s*"((?:[^"\\]|\\.)*)"', t)
        if m: return {"reply": m.group(1), "mission": None, "topic": "", "safety_flag": None, "learning_note": ""}
        return None

def llm(messages):
    """cache-first; calls are sequential (client awaits each reply)."""
    h = hashlib.sha256(json.dumps(messages, sort_keys=True).encode()).hexdigest()
    cp = P("cache", h + ".json")
    if os.path.exists(cp):
        c = json.load(open(cp, encoding="utf-8"))
        logline({"ts": time.time(), "id": c.get("id"), "model": MODEL, "tokens": c.get("usage", {}).get("total_tokens"), "cost": 0, "cache_hit": True})
        return c
    guard()
    body = json.dumps({"model": MODEL, "messages": messages, "temperature": 0.4, "max_tokens": 1200, "reasoning": {"effort": "low"}, "usage": {"include": True}}).encode()
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", body,
        {"Authorization": "Bearer " + key(), "Content-Type": "application/json"})
    t0 = time.time()
    c = json.load(urllib.request.urlopen(req, timeout=60))
    u = c.get("usage", {})
    logline({"ts": t0, "id": c.get("id"), "model": c.get("model", MODEL), "tokens": u.get("total_tokens"), "cost": u.get("cost"), "latency_s": round(time.time() - t0, 2), "cache_hit": False})
    json.dump(c, open(cp, "w", encoding="utf-8"))
    return c

def system(wind):
    s, p, turn = rj("data/settings.json", {}), rj("data/profile.json", {}), len(rj("data/session.json", [])) // 2 + 1
    return ("You are %s, %s, a kind learning companion for a child aged %s.\n"
     "Replies <=40 words, one idea, ask a question back when natural.\n"
     "Allowed topics: %s. Goal: %s. Innocent off-list topic: answer briefly, suggest asking a grown-up.\n"
     "Safety: never ask for or accept names, address, school, phone, photos, contacts. Unsafe, adult, violent, scary, medical or secret-keeping requests: do not answer, redirect to an allowed topic, set safety_flag (\"unsafe_topic\"|\"personal_info\"|\"distress\"). Never persuade the child to keep chatting.\n"
     "Turn %d: every 3rd turn add a one-sentence offline mission (draw, ask a parent, go outside, read together); else null.\n"
     "%s"
     "Return ONLY JSON: {\"reply\":str,\"mission\":str|null,\"topic\":str,\"safety_flag\":str|null,\"learning_note\":str}") % (
        p.get("name", "Pip"), p.get("persona", "a friendly dragon"), s.get("age_band"), ", ".join(s.get("topics", [])), s.get("goal"), turn,
        "wind_down is TRUE: goodbye <=25 words, one mission, no question.\n" if wind else "")

SUMMARY_PROMPT = ("Summarise this child's session for a parent. Return ONLY JSON: "
    '{"learned":[str],"time_used_min":int,"mood":"happy"|"curious"|"restless"|"upset","flags":[str],"suggestion_for_parent":str (<=30 words, one offline activity)}')

def chat(text, wind):
    hist = rj("data/session.json", [])
    turn = len(hist) // 2 + 1
    if UNSAFE.search(text):
        out = {"reply": REDIRECT, "mission": None, "topic": "blocked", "safety_flag": "keyword_precheck", "learning_note": ""}
        logline({"ts": time.time(), "id": None, "model": MODEL, "tokens": 0, "cost": 0, "cache_hit": False, "note": "keyword redirect, no model call"})
    else:
        msgs = [{"role": "system", "content": system(wind)}] + hist[-8:] + [{"role": "user", "content": text}]
        out = None
        for _ in range(2):
            c = llm(msgs); out = parse(c["choices"][0]["message"]["content"] or "")
            if out: break
            h = hashlib.sha256(json.dumps(msgs, sort_keys=True).encode()).hexdigest()
            if os.path.exists(P("cache", h + ".json")): os.remove(P("cache", h + ".json"))  # never cache unparseable output
        out = out or {"reply": "Hmm, let's try that again!", "mission": None, "topic": "", "safety_flag": None, "learning_note": ""}
    if turn % 3 == 0 and not out.get("mission"): out["mission"] = "Draw what we talked about and show a grown-up!"
    hist += [{"role": "user", "content": text}, {"role": "assistant", "content": out["reply"]}]
    wj("data/session.json", hist)
    notes = rj("data/notes.json", [])
    notes.append({"turn": turn, "topic": out.get("topic"), "note": out.get("learning_note"), "flag": out.get("safety_flag"), "text": text if out.get("safety_flag") else None})
    wj("data/notes.json", notes)
    out["turn"] = turn
    return out

def end(minutes):
    notes = rj("data/notes.json", [])
    flags = [n for n in notes if n.get("flag")]
    msgs = [{"role": "system", "content": SUMMARY_PROMPT},
            {"role": "user", "content": json.dumps({"learning_notes": [n["note"] for n in notes], "topics": [n["topic"] for n in notes], "flags": [n["flag"] for n in flags], "minutes": minutes})}]
    try: s = parse(llm(msgs)["choices"][0]["message"]["content"]) or {}
    except Exception as e: s = {"learned": [n["note"] for n in notes if n["note"]], "mood": "curious", "suggestion_for_parent": "Fallback summary (%s)" % type(e).__name__}
    s["flags"] = [{"turn": n["turn"], "flag": n["flag"], "child_said": n["text"]} for n in flags]
    sums = rj("data/summaries.json", []); sums.append(s); wj("data/summaries.json", sums)
    return s

# --- kid play-pad state (additive): mission board, XP, emoji reactions ---
STARTER = [{"id": "s1", "title": "Draw Pip and show a grown-up", "emoji": "🎨", "xp": 15, "by": "starter", "done": False}]
def tasks():
    t, notes = rj("data/tasks.json", STARTER), rj("data/notes.json", [])
    return {"tasks": t, "xp": sum(x["xp"] for x in t if x.get("done")) + 5 * sum(1 for n in notes if not n.get("flag")),
            "reactions": rj("data/reactions.json", [])[-5:]}
def add_task(d, parent):
    title = str(d.get("title", "")).strip()[:80]
    if not title: raise ValueError("title required")
    t = rj("data/tasks.json", STARTER)
    if not parent and any(x["title"] == title for x in t): return tasks()  # buddy mission already on the board
    t.append({"id": "t%d" % (time.time() * 1000), "title": title, "emoji": str(d.get("emoji", "⭐"))[:4],
              "xp": min(50, max(5, int(d.get("xp", 20)))) if parent else 10, "by": "parent" if parent else "buddy", "done": False})
    wj("data/tasks.json", t); return tasks()

def proof():
    lp = P("proof", "openrouter_log.jsonl")
    log = [json.loads(l) for l in open(lp, encoding="utf-8")] if os.path.exists(lp) else []
    return {"log": log, "key_before": rj("proof/key_before.json", {}).get("data", {}).get("usage"), "key_after": rj("proof/key_after.json", {}).get("data", {}).get("usage"),
            "live_cost": sum(float(l.get("cost") or 0) for l in log if not l["cache_hit"]), "live_calls": sum(1 for l in log if l.get("id") and not l["cache_hit"]), "cap": CAP}

class H(BaseHTTPRequestHandler):
    def send(self, o, code=200, ct="application/json"):
        b = o if isinstance(o, bytes) else json.dumps(o).encode()
        self.send_response(code); self.send_header("Content-Type", ct); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def authed(self): return self.headers.get("X-Parent-Token") in TOKENS
    def do_GET(self):
        if self.path.split("?")[0] == "/": return self.send(open(P("index.html"), "rb").read(), ct="text/html; charset=utf-8")
        if self.path == "/api/settings": return self.send({"settings": {k: v for k, v in rj("data/settings.json", {}).items() if not k.startswith("pin_")}, "profile": rj("data/profile.json", {})})
        if self.path == "/api/proof": return self.send(proof())
        if self.path == "/api/summaries":
            if not self.authed(): return self.send({"error": "parent PIN required"}, 401)
            return self.send({"summaries": rj("data/summaries.json", []), "notes": rj("data/notes.json", [])})
        if self.path == "/api/tasks": return self.send(tasks())
        if self.path == "/api/live":
            if not self.authed(): return self.send({"error": "parent PIN required"}, 401)
            return self.send(dict(tasks(), session=rj("data/session.json", []), notes=rj("data/notes.json", []), summaries=rj("data/summaries.json", [])))
        self.send({"error": "nf"}, 404)
    def do_POST(self):
        d = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        try:
            if self.path == "/api/unlock":
                st = rj("data/settings.json", {})
                if secrets.compare_digest(pin_hash(st["pin_salt"], str(d.get("pin", ""))), st["pin_hash"]):
                    t = secrets.token_hex(16); TOKENS.add(t); return self.send({"token": t})
                return self.send({"error": "wrong PIN"}, 403)
            if self.path in ("/api/companion", "/api/settings") and not self.authed(): return self.send({"error": "parent PIN required"}, 401)
            if self.path == "/api/companion": wj("data/profile.json", d); return self.send(d)
            if self.path == "/api/settings":
                old = rj("data/settings.json", {}); d.update({k: v for k, v in old.items() if k.startswith("pin_")}); wj("data/settings.json", d)
                return self.send({k: v for k, v in d.items() if not k.startswith("pin_")})
            if self.path == "/api/reset": wj("data/session.json", []); wj("data/notes.json", []); wj("data/tasks.json", STARTER); wj("data/reactions.json", []); return self.send({"ok": 1})
            if self.path == "/api/tasks":
                if d.get("by") == "parent" and not self.authed(): return self.send({"error": "parent PIN required"}, 401)
                return self.send(add_task(d, d.get("by") == "parent"))
            if self.path == "/api/tasks/done":
                t = rj("data/tasks.json", STARTER)
                for x in t:
                    if x["id"] == d.get("id"): x["done"] = bool(d.get("done", True))
                wj("data/tasks.json", t); return self.send(tasks())
            if self.path == "/api/react":
                r = rj("data/reactions.json", []); r.append({"ts": time.time(), "emoji": str(d.get("emoji", ""))[:4]}); wj("data/reactions.json", r[-50:]); return self.send({"ok": 1})
            if self.path == "/api/chat": return self.send(chat(d["text"], bool(d.get("wind_down"))))
            if self.path == "/api/end": return self.send(end(d.get("minutes", 0)))
        except Exception as e: return self.send({"error": str(e)}, 500)
        self.send({"error": "nf"}, 404)
    def log_message(self, *a): pass

def selftest():
    assert UNSAFE.search("What's our home address?") and not UNSAFE.search("why is the sky blue")
    assert parse('```json\n{"reply":"hi","mission":null}\n```')["reply"] == "hi"
    assert parse('junk "reply": "yo" junk')["reply"] == "yo"
    try: guard(CAP); raise SystemExit("guard did not trip")
    except RuntimeError: pass
    assert pin_hash("a", "2468") != pin_hash("b", "2468")
    try: add_task({"title": " "}, True); raise SystemExit("empty task accepted")
    except ValueError: pass
    print("selftest ok")

if __name__ == "__main__":
    if "--selftest" in sys.argv: selftest()
    else:
        ensure_pin()
        port = int(os.environ.get("PORT", 8765)); print("http://127.0.0.1:%d" % port)
        ThreadingHTTPServer((os.environ.get("HOST", "127.0.0.1"), port), H).serve_forever()
