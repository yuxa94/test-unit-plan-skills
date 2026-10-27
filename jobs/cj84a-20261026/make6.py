t = open(r"C:\temp\cj84a\build5.py", encoding="utf-8").read()
old_w = '''win_rules = [{"room": n, "type": "double"} for n in ("거실", "침실1", "침실2", "침실3", "주방/식당", "드레스룸")] + \\
            [{"room": "하향식피난구", "type": "outdoor_unit", "width": 1000, "facing": "exterior"}]'''
assert old_w in t, "win_rules"
new_w = '''win_rules = [  # profile: plan-relative side (+y = N) and width per room (user_confirmed: 원본 84A 값)
    {"room": "거실", "type": "double", "side": "S", "width": 3600},
    {"room": "침실1", "type": "double", "side": "S", "width": 1500},
    {"room": "침실2", "type": "double", "side": "S", "width": 1800},
    {"room": "침실3", "type": "double", "side": "S", "width": 1800},
    {"room": "주방/식당", "type": "double", "side": "N", "width": 1500},
    {"room": "드레스룸", "type": "double", "side": "N", "width": 1000},
    {"room": "하향식피난구", "type": "outdoor_unit", "side": "S", "width": 1000, "facing": "exterior"}]'''
t = t.replace(old_w, new_w)
old_d = 'doors, door_issues = place_doors(model, [r for r in door_rules if r["room"] not in ("욕실1", "욕실2")], taken=taken)'
assert old_d in t, "doors"
t = t.replace(old_d, 'CORRIDOR_MAX = 1800\n' + old_d.replace("taken=taken)", "taken=taken, corridor_max=CORRIDOR_MAX)"))
t = t.replace('P["doors"] = {"rules": {"value": door_rules, "status": UC}, "source": {"value": "rule", "status": UC}}',
              'P["doors"] = {"rules": {"value": door_rules, "status": UC}, "source": {"value": "rule", "status": UC}, "corridor_max_mm": {"value": 1800, "status": UC}}')
t = t.replace("\\v005", "\\v006").replace("C:/temp/cj84a/v005/", "C:/temp/cj84a/v006/")
t = t.replace("cj84A-basic-v005.dwg", "cj84A-basic-v006.dwg").replace("operations_v005", "operations_v006")
t = t.replace('-401"', '-501"').replace("std-401.lsp", "std-501.lsp").replace('"rule-v005"', '"rule-v006"')
t = t.replace("v005 — 주방: 쿡탑=창(환기) 쪽 끝, 싱크=거실 쪽 끝 (arrangement 프로파일)", "v006 — 창: 실별 방위·폭 프로파일, 문: 복도·홀(문 앞 폭 1800 이하) 우선")
open(r"C:\temp\cj84a\build6.py", "w", encoding="utf-8").write(t)
print(t.count("v005"), t.count("-501"), "corridor_max_mm" in t)
