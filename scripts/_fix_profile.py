#!/usr/bin/env python3
"""WSL /root/.profile içindeki .cargo/env source komutunu conditional yap.
Lord 4 Haz: bat walker boot "g: No such file" → .profile satır 10 .cargo/env eksik."""
import pathlib

p = pathlib.Path("/root/.profile")
txt = p.read_text()
old = '. "$HOME/.cargo/env"'
new = '[ -f "$HOME/.cargo/env" ] && . "$HOME/.cargo/env"'

if new in txt:
    print("ALREADY_FIXED")
elif old in txt:
    p.write_text(txt.replace(old, new))
    print("OK fixed")
else:
    print(f"NOT_FOUND. Tail: {txt[-200:]!r}")
