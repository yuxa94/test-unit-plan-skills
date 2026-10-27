p = r"C:\temp\cj84a\build3.py"
t = open(p, encoding="utf-8").read()
t = t.replace("\\v002", "\\v003")
# UBR = body block + panel block
t = t.replace('op("bath-201", [insert(f, "FUR") for f in ubr], "ms o")',
              'op("bath-201", [insert(f, "FUR") for f in ubr] + [insert(dict(f["panel"]), f["panel"]["layer"]) for f in ubr], "ms o")')
t = t.replace('BLOCKS = sorted({f["block"] for f in fixtures if f.get("block")})',
              'BLOCKS = sorted({f["block"] for f in fixtures if f.get("block")} | {f["panel"]["block"] for f in ubr})')
open(p, "w", encoding="utf-8").write(t)
print(t.count("v002"), t.count('f["panel"]'))
