t = open(r"C:\temp\cj84a\build6.py", encoding="utf-8").read()
rep = {
    '{"room": "현관", "to": "__core__", "width": 1100, "swing": "out"}': '{"room": "현관", "to": "__core__", "width": 1100, "swing": "out", "position": "center"}',
    '{"room": "침실1", "to": ["거실", "주방/식당", "현관"], "width": 900}': '{"room": "침실1", "to": ["거실", "주방/식당", "현관"], "width": 900, "position": "corner"}',
    '{"room": "침실2", "to": ["거실", "현관", "주방/식당"], "width": 900}': '{"room": "침실2", "to": ["거실", "현관", "주방/식당"], "width": 900, "position": "corner"}',
    '{"room": "침실3", "to": ["거실", "현관", "주방/식당"], "width": 900}': '{"room": "침실3", "to": ["거실", "현관", "주방/식당"], "width": 900, "position": "corner"}',
    '{"room": "팬트리", "to": ["주방/식당", "거실", "현관"], "width": 800}': '{"room": "팬트리", "to": ["주방/식당", "거실", "현관"], "width": 800, "position": "center"}',
    '{"room": "하향식피난구", "to": ["발코니1"], "width": 750, "type": "sliding"}': '{"room": "하향식피난구", "to": ["발코니1"], "width": 750, "type": "sliding", "position": "entry", "jamb": 150}',
}
for a, b in rep.items():
    assert a in t, a
    t = t.replace(a, b)
old = "taken=taken, corridor_max=CORRIDOR_MAX)"
assert old in t
t = t.replace(old, "taken=taken, corridor_max=CORRIDOR_MAX, jamb=DOOR_JAMB)")
t = t.replace("CORRIDOR_MAX = 1800\n", "CORRIDOR_MAX = 1800\nDOOR_JAMB = 100   # profile: corner face -> opening (user_confirmed)\n")
t = t.replace('"corridor_max_mm": {"value": 1800, "status": UC}}',
              '"corridor_max_mm": {"value": 1800, "status": UC}, "jamb_mm": {"value": 100, "status": UC}, '
              '"position": {"value": {"침실·드레스룸·욕실": "corner", "현관·팬트리": "center", "하향식피난구": "entry(미지정, v006 유지)"}, "status": UC}}')
t = t.replace("\\v006", "\\v007").replace("C:/temp/cj84a/v006/", "C:/temp/cj84a/v007/")
t = t.replace("cj84A-basic-v006.dwg", "cj84A-basic-v007.dwg").replace("operations_v006", "operations_v007")
t = t.replace('-501"', '-601"').replace("std-501.lsp", "std-601.lsp").replace('"rule-v006"', '"rule-v007"')
t = t.replace("v006 — 창: 실별 방위·폭 프로파일, 문: 복도·홀(문 앞 폭 1800 이하) 우선", "v007 — 문 위치: 실 모서리+문틀 여유 100 / 가운데 (프로파일)")
open(r"C:\temp\cj84a\build7.py", "w", encoding="utf-8").write(t)
print(t.count("v006"), t.count("-601"), "DOOR_JAMB" in t)
