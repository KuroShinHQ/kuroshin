#!/usr/bin/env python3
import json
d = json.load(open('/mnt/c/Kuroshin/scripts/iron_inquisitor/reports/inquisitor_20260705_174821.json'))
for t in d:
    if t['id'] in ['model-reason-01','model-reason-02','model-reason-03']:
        print(f'{t["id"]}: status={t["status"]} output={t["output"][:150]}')
