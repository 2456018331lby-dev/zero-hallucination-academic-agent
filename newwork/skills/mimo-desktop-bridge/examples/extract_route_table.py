import re, sys

PATH = r"C:\Users\24560\AppData\Local\Programs\Xiaomi MiMo\resources\app.asar"

def region(center, span=40000):
    with open(PATH, "rb") as f:
        f.seek(max(0, center - span // 2))
        return f.read(span).decode("latin-1", errors="replace")

def find_after(anchor, before, length):
    """Locate anchor in the whole file, return text window."""
    with open(PATH, "rb") as f:
        pos = 0
        carry = b""
        while True:
            chunk = f.read(8 * 1024 * 1024)
            if not chunk:
                return ""
            buf = carry + chunk
            i = buf.find(anchor)
            if i >= 0:
                start = max(0, i - before)
                with open(PATH, "rb") as g:
                    g.seek(max(0, pos + i - before))
                    return g.read(length).decode("latin-1", errors="replace")
            carry = buf[-64:]
            pos += len(chunk)

anchor = sys.argv[1].encode() if len(sys.argv) > 1 else b"function xY("
txt = find_after(anchor, 200, 30000)
print(txt)
