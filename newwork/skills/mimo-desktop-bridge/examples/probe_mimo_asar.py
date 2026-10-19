import re, sys, io

PATH = r"C:\Users\24560\AppData\Local\Programs\Xiaomi MiMo\resources\app.asar"

def dump_region(center, span=40000):
    with open(PATH, "rb") as f:
        f.seek(max(0, center - span // 2))
        data = f.read(span)
    return data.decode("latin-1", errors="replace")

def main():
    off = int(sys.argv[1]) if len(sys.argv) > 1 else 16091773
    region = dump_region(off)
    print("=== QUOTED PATH-LIKE STRINGS IN REGION ===")
    paths = sorted(set(re.findall(r'"(/[A-Za-z0-9_\-/{}:.]{1,70})"', region)))
    for p in paths:
        print(p)
    print()
    print("=== METHOD CALLS IN REGION ===")
    calls = sorted(set(re.findall(r'\.(get|post|put|delete|patch|all|use)\(\s*"(/[A-Za-z0-9_\-/{}:.]{1,70})"', region)))
    for m, p in calls:
        print(m.upper(), p)
    print()
    print("=== CONTEXT AROUND TOKEN ERROR ===")
    idx = region.find("invalid or missing token")
    if idx >= 0:
        print(region[max(0, idx - 3000): idx + 1500])

main()
