import sys
import os
# Mocking send_telegram to avoid actual spam during test
def mock_send_telegram(msg):
    print(f"TELEGRAM SENT: {msg}")

sys.path.insert(0, "C:/Kuroshin/scripts")
import auto_integrator as ai
ai.send_telegram = mock_send_telegram

items = ai.scan_new_reports()
print(f"Found {len(items)} items")
for i in items:
    print(f"Checking {i['id']}")
    if i['id'] == 'mradermacher_ibm_gpt5_4_coder_1b_i1_gguf':
        print("Processing target item...")
        ai.process_item(i)
