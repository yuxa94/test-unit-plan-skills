t = open(r"C:\temp\cj84a\build9.py", encoding="utf-8").read()
old = "taken=taken, corridor_max=CORRIDOR_MAX, jamb=DOOR_JAMB)"
assert old in t, "doors call"
t = t.replace(old, 'taken=taken, corridor_max=CORRIDOR_MAX, jamb=DOOR_JAMB, corridor_tie="living")')
t = t.replace('"jamb_mm": {"value": 100, "status": UC},', '"jamb_mm": {"value": 100, "status": UC}, "corridor_tie": {"value": "living", "status": UC},')
t = t.replace("\\v009", "\\v010").replace("C:/temp/cj84a/v009/", "C:/temp/cj84a/v010/")
t = t.replace("cj84A-basic-v009.dwg", "cj84A-basic-v010.dwg").replace("operations_v009", "operations_v010")
t = t.replace('-801"', '-901"').replace("std-801.lsp", "std-901.lsp").replace('"rule-v009"', '"rule-v010"')
t = t.replace("v009 — 세탁기: 외벽 우선 → 수전·배수 거리", "v010 — 문: 홀 동률 시 거실 쪽 모서리")
open(r"C:\temp\cj84a\build10.py", "w", encoding="utf-8").write(t)
print(t.count("v009"), t.count("-901"), 'corridor_tie="living"' in t)
