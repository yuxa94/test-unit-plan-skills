import glob, re, sys
for f in sorted(glob.glob(r"C:\temp\cj84a\v010\ops\*.lsp")):
    s = open(f, encoding="utf-8").read()
    s2 = re.sub(r'"(?:\\.|[^"\\])*"', '""', s)
    print(f.split("\\")[-1], s2.count("(") - s2.count(")"))
