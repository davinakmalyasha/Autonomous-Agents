import requests, time
time.sleep(3)

# Test 1: hello
print("=== Test 1: hello ===")
r = requests.post(
    'http://127.0.0.1:8000/api/run',
    json={'prompt': 'hello', 'model': 'Automatic Fallback', 'temperature': 0.7, 'workspace_path': r'd:\MyProject\LangChain'},
    timeout=30,
)
print(f"Status: {r.status_code}")
for line in r.text.split('\n'):
    if line.startswith('data:'):
        import json
        try:
            data = json.loads(line[5:].strip())
            log = data.get('live_terminal_log', '')
            if log:
                print(f"Response: {log.strip()}")
        except:
            pass

# Test 2: what project is this?
print("\n=== Test 2: what project is this? ===")
r = requests.post(
    'http://127.0.0.1:8000/api/run',
    json={'prompt': 'what project is this?', 'model': 'Automatic Fallback', 'temperature': 0.7, 'workspace_path': r'd:\MyProject\LangChain'},
    timeout=30,
)
print(f"Status: {r.status_code}")
for line in r.text.split('\n'):
    if line.startswith('data:'):
        import json
        try:
            data = json.loads(line[5:].strip())
            log = data.get('live_terminal_log', '')
            if log:
                print(f"Response: {log.strip()}")
        except:
            pass
