t = open(r"C:\temp\cj84a\build7.py", encoding="utf-8").read()
# reuse build.py sections, but with the v008 zoning and the extra balcony kind
old = 'SRCPY = open(JOB + r"\\build.py", encoding="utf-8").read().splitlines()'
assert old in t, "SRCPY"
t = t.replace(old, 'SRCPY = (open(JOB + r"\\build.py", encoding="utf-8").read()\n'
                   '         .replace(r"\\zoning.json", r"\\zoning_v008.json")\n'
                   '         .replace(\'"발코니2": "balcony",\', \'"발코니2": "balcony", "발코니2-2": "balcony",\')).splitlines()')
old_t = 'if f["name"] in ("발코니1", "발코니2", "하향식피난구"):'
assert old_t in t, "tile"
t = t.replace(old_t, 'if f["name"] in ("발코니1", "발코니2", "발코니2-2", "하향식피난구"):')
# label for the new balcony part (no label in the reference sheet)
old_l = 'model2 = {"version": 1'
assert old_l in t, "labels"
t = t.replace(old_l, 'from upgeom import centroid as _c\n'
                     'for s in spaces:\n'
                     '    if s["name"] == "발코니2-2": labels.append({"text": "발코니2-2", "at": [round(_c(s["polygon"])[0]) - 400, round(_c(s["polygon"])[1])]})\n'
                     + old_l, 1)
t = t.replace("\\v007", "\\v008").replace("C:/temp/cj84a/v007/", "C:/temp/cj84a/v008/")
t = t.replace("cj84A-basic-v007.dwg", "cj84A-basic-v008.dwg").replace("operations_v007", "operations_v008")
t = t.replace('-601"', '-701"').replace("std-601.lsp", "std-701.lsp").replace('"rule-v007"', '"rule-v008"')
t = t.replace("v007 — 문 위치: 실 모서리+문틀 여유 100 / 가운데 (프로파일)", "v008 — 발코니2 조닝을 원본 바닥타일 범위로, 세탁기 배치")
open(r"C:\temp\cj84a\build8.py", "w", encoding="utf-8").write(t)
print(t.count("v007"), t.count("-701"), "zoning_v008" in t)
