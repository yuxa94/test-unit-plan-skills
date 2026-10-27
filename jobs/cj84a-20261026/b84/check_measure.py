import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Planby Technologies\Desktop\2026\Autocad_mcp_test\unit-plan-skills\unit-plan\scripts")
import run_reference_unit as R

OFF = {("V", 0): (-125, 125, "RC"), ("H", 7150): (-125, 125, "RC"), ("H", 10335): (-200, 0, "RC"),
       ("H", 7010): (-125, 125, "RC"), ("V", 5570): (-125, 125, "RC"), ("H", 9000): (-125, 125, "RC"),
       ("V", 6340): (-112, 112, "RC"), ("V", 14630): (55, 305, "RC"), ("H", 0): (0, 200, "RC"),
       ("H", 9745): (-200, 0, "RC"), ("H", 8140): (-10, 190, "RC"), ("H", 1680): (-190, 10, "RC"),
       ("H", 4035): (-120, 80, "RC"), ("V", 12780): (-60, 60, "RC"),
       ("V", 12640): (-35, 65, "DRY"), ("V", 1780): (-35, 65, "DRY"), ("H", 5555): (-65, 35, "DRY"),
       ("H", 8145): (-15, 185, "MAS"), ("H", 8585): (-15, 175, "MAS"), ("V", 10080): (-15, 175, "MAS"),
       ("H", 1500): (-175, 15, "MAS"), ("H", 1675): (-175, 15, "MAS"), ("H", 7090): (-20, 55, "DRY"), ("V", 11390): (-70, 5, "DRY")}
rows = R.load_tsv(r"C:\temp\cj84a\input\84A_basic_L1.tsv")
lines = [(r[1], *map(float, r[2:6])) for r in rows if r[0] == "LINE"]
walls = R.build_walls(lines, {"walls": {"party_axes": [["V", 0]]}})
ok = bad = 0
for w in walls:
    key = (w["orient"], w["axis_coord"])
    if key not in OFF: continue
    lo, hi, mat = OFF[key]
    d = max(abs(w["lo"] - lo), abs(w["hi"] - hi))
    flag = "OK " if d <= 25 and w["material"] == mat else "DIFF"
    ok += flag == "OK "; bad += flag != "OK "
    print(f'{flag} {key}: manual ({lo},{hi},{mat})  auto ({round(w["lo"])},{round(w["hi"])},{w["material"]}) {w["basis"]}')
print("ok", ok, "diff", bad)
