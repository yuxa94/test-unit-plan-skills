import re
for p in (r"C:\temp\cj84a\build3.py", r"C:\temp\cj84a\build2.py"):
    t = open(p, encoding="utf-8").read()
    t = t.replace('def run(a, b): exec(compile("\\n".join(SRCPY[a - 1:b - 1]), "build.py", "exec"), G)',
                  'def _at(tag): return next(i for i, l in enumerate(SRCPY) if l.startswith("# ----") and tag in l)\n'
                  'def run_sec(start, end):\n'
                  '    a = 0 if start is None else _at(start)\n'
                  '    exec(compile("\\n".join(SRCPY[a:_at(end)]), "build.py", "exec"), G)')
    t = t.replace("run(1, 112)", 'run_sec(None, "openings from source parts")')
    t = t.replace("run(136, 234)", 'run_sec("wall outlines", "room names from sheet")')
    open(p, "w", encoding="utf-8").write(t)
    print(p, t.count("run_sec("))
