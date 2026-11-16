from pathlib import Path
import shutil

p = Path("src/pages/LearnConcept.jsx")
shutil.copy2(p, Path("src/pages/LearnConcept.jsx.backup-unicode"))

s = p.read_text(encoding="utf-8-sig")

replacements = {
    "\u00e2\u0153\u201c": "\u2713",
    "\u00e2\u2020\u2019": "\u2192",
    "\u00e2\u20ac\u201d": "\u2014",
    "\u00c2\u00b7": "\u00b7",
}

for old, new in replacements.items():
    s = s.replace(old, new)

p.write_text(s, encoding="utf-8")

print("LearnConcept Unicode repair completed.")
