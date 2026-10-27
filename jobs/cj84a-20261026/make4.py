t = open(r"C:\temp\cj84a\build3.py", encoding="utf-8").read()
old = 'kcfg = {"room": "주방/식당", "layout": "I", "depth": 650, "fridge": 900, "min_len": 1800,'
assert old in t
t = t.replace(old, 'kcfg = {"room": "주방/식당", "layout": "I", "depth": 650, "fridge_position": "outside", "fridge_width": 900, "min_len": 1800,')
t = t.replace("\\v003", "\\v004").replace("C:/temp/cj84a/v003/", "C:/temp/cj84a/v004/")
t = t.replace("cj84A-basic-v003.dwg", "cj84A-basic-v004.dwg").replace("operations_v003", "operations_v004")
t = t.replace('-201"', '-301"').replace("std-201.lsp", "std-301.lsp").replace('"rule-v003"', '"rule-v004"')
t = t.replace("v003 — UBR 실제 외곽선 + UBR 문 기준 욕실문", "v004 — 주방: 냉장고 위치 프로파일, 싱크는 창 쪽 끝")
open(r"C:\temp\cj84a\build4.py", "w", encoding="utf-8").write(t)
print(t.count("v003"), t.count("-301"))
