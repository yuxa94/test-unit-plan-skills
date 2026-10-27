t = open(r"C:\temp\cj84a\build8.py", encoding="utf-8").read()
old = '"washer": {"block": "세탁기-850", "room": "발코니2"}}'
assert old in t, "washer cfg"
t = t.replace(old, '"washer": {"block": "세탁기-850", "room": "발코니2", "priority": "exterior_first", '
                   '"water_points": [[11905, 8406], [11755, 8406], [11395, 8400]]}}')   # 원본 수전 2 + FD (profile, observed)
t = t.replace("\\v008", "\\v009").replace("C:/temp/cj84a/v008/", "C:/temp/cj84a/v009/")
t = t.replace("cj84A-basic-v008.dwg", "cj84A-basic-v009.dwg").replace("operations_v008", "operations_v009")
t = t.replace('-701"', '-801"').replace("std-701.lsp", "std-801.lsp").replace('"rule-v008"', '"rule-v009"')
t = t.replace("v008 — 발코니2 조닝을 원본 바닥타일 범위로, 세탁기 배치", "v009 — 세탁기: 외벽 우선 → 수전·배수 거리")
open(r"C:\temp\cj84a\build9.py", "w", encoding="utf-8").write(t)
print(t.count("v008"), t.count("-801"))
