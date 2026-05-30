#!/usr/bin/env python3
"""Inspect GGUF model metadata - prove native max context."""
import sys
from gguf import GGUFReader

if len(sys.argv) < 2:
    print("usage: _inspect_gguf.py <path.gguf>")
    sys.exit(1)

reader = GGUFReader(sys.argv[1])
wanted = [
    "context_length",
    "embedding_length",
    "head_count",
    "head_count_kv",
    "block_count",
    "rope.freq_base",
    "rope.dimension_count",
    "rope.scaling",
    "rope.dimension_sections",
    "general.architecture",
    "general.name",
]
for fname, field in reader.fields.items():
    fl = fname.lower()
    if any(k in fl for k in wanted):
        try:
            parts = field.parts
            data_idx = field.data
            if data_idx:
                vals = [parts[i].tolist() if hasattr(parts[i], "tolist") else parts[i] for i in data_idx]
                if len(vals) == 1:
                    v = vals[0]
                    if isinstance(v, list) and len(v) == 1:
                        v = v[0]
                    print(f"{fname} = {v}")
                else:
                    print(f"{fname} = {vals}")
            else:
                print(f"{fname} = (no data)")
        except Exception as e:
            print(f"{fname} = (err: {e})")
