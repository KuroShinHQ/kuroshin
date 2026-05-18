#!/bin/bash
curl -s -m 120 -X POST http://127.0.0.1:9002/task \
  -H 'Content-Type: application/json' \
  -d '{"task": "Python agno framework hakkinda 2 cumle bilgi ver."}' \
  2>&1
