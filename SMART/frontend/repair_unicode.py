from pathlib import Path
import shutil

p = Path("src/pages/dashboard.jsx")
shutil.copy2(p, Path("src/pages/dashboard.jsx.backup-unicode"))

s = p.read_text(encoding="utf-8-sig")

replacements = {
    "\u00e2\u0152\u02dc": "\u2318",
    "\u00e2\u0153\u00a6": "\u2726",
    "\u00e2\u0153\u00a7": "\u2727",
    "\u00e2\u0153\u201c": "\u2713",
    "\u00e2\u2013\u00a0": "\u25a0",
    "\u00e2\u2020\u2014": "\u2197",
    "\u00e2\u2020\u2019": "\u2192",
    "\u00c2\u00b7": "\u00b7",
}

for old, new in replacements.items():
    s = s.replace(old, new)

p.write_text(s, encoding="utf-8")
print("Repair complete. Remaining non-ASCII sequences:")
import re
print([(repr(x), [hex(ord(c)) for c in x])
       for x in sorted(set(re.findall(r'[^\x00-\x7F]+', s)))])
