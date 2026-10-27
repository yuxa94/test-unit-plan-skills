t = open(r"C:\temp\cj84a\build4.py", encoding="utf-8").read()
old = '"fridge_position": "outside", "fridge_width": 900,'
assert old in t
t = t.replace(old, old + ' "arrangement": "cooktop_window", "living": ["거실"],')
t = t.replace("\\v004", "\\v005").replace("C:/temp/cj84a/v004/", "C:/temp/cj84a/v005/")
t = t.replace("cj84A-basic-v004.dwg", "cj84A-basic-v005.dwg").replace("operations_v004", "operations_v005")
t = t.replace('-301"', '-401"').replace("std-301.lsp", "std-401.lsp").replace('"rule-v004"', '"rule-v005"')
t = t.replace("v004 — 주방: 냉장고 위치 프로파일, 싱크는 창 쪽 끝", "v005 — 주방: 쿡탑=창(환기) 쪽 끝, 싱크=거실 쪽 끝 (arrangement 프로파일)")
open(r"C:\temp\cj84a\build5.py", "w", encoding="utf-8").write(t)
print(t.count("v004"), t.count("-401"))
