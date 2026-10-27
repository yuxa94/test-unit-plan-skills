"""Regression: recompute 84A v008 with the current skill scripts into v008chk and diff against v008."""
import json, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")
t = open(r"C:\temp\cj84a\build8.py", encoding="utf-8").read()
t = t.replace("\\v008", "\\v008chk").replace("C:/temp/cj84a/v008/", "C:/temp/cj84a/v008chk/")
t = t.replace("cj84A-basic-v008.dwg", "cj84A-basic-v008chk.dwg").replace("operations_v008", "operations_v008chk")
open(r"C:\temp\cj84a\build8chk.py", "w", encoding="utf-8").write(t)
r = subprocess.run([sys.executable, "-I", r"C:\temp\cj84a\build8chk.py"], capture_output=True, text=True, encoding="utf-8")
if r.returncode: print(r.stderr[-2000:]); raise SystemExit(1)
a = json.load(open(r"C:\temp\cj84a\v008\model.json", encoding="utf-8"))
b = json.load(open(r"C:\temp\cj84a\v008chk\model.json", encoding="utf-8"))
def key_open(m): return sorted((o["kind"], o["room"], o.get("to", ""), o["wall"], round(o["span"][0]), round(o["span"][1])) for o in m["openings"])
def key_fix(m): return sorted((f["kind"], f["space"], tuple(round(v) for v in (f.get("footprint") or f.get("rect")))) for f in m["fixtures"])
for name, fa, fb in (("openings", key_open(a), key_open(b)), ("fixtures", key_fix(a), key_fix(b))):
    if fa == fb: print(f"{name}: 동일 ({len(fa)}개)")
    else:
        print(f"{name}: 차이 있음")
        for x in sorted(set(fa) ^ set(fb)): print("   ", "v008" if x in fa else "now ", x)
print("kitchen basis:", [(f["kind"], f["basis"]) for f in b["fixtures"] if f["space"] == "주방/식당"])
