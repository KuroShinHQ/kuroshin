#!/usr/bin/env python3
"""Quick episodic baseline count."""
import sys
sys.path.insert(0, "/mnt/c/Kuroshin/scripts")
from kuroshin_episodic import EpisodicMemory
em = EpisodicMemory()
print(f"count={em.collection_count}")
