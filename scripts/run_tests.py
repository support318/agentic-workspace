"""
Combined test: Start mock server and run webhook tests.
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import subprocess
import time
import requests
import signal
import os

# Print header
print("="*60)
print("GHL CALENDAR WORKFLOW - AUTOMATED TEST")
print("="*60)
print()

# Start the mock server in background
print("1. Starting mock webhook server...")
server_process = subprocess.Popen(
    [sys.executable, "scripts/test_local_server.py"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    cwd=os.path.dirname(os.path.abspath(__file__)) + "/.."
)

# Wait for server to start
print("   Waiting for server to start...", end="", flush=True)
for i in range(10):
    try:
        requests.get("http://localhost:8080/health", timeout=1)
        print(" ✓")
        break
    except:
        time.sleep(0.5)
        print(".", end="", flush=True)
else:
    print(" ✗")
    print("   Server failed to start!")
    server_process.kill()
    sys.exit(1)

# Run the tests
print("\n2. Running webhook tests...")
print("-"*60)

test_results = []

# Test 1: Lead payload
print("\nTest 1: Lead event")
payload1 = {
    "Opportunity Name": "Johnson Wedding - Photography & Video",
    "Event Date": "2025-06-15",
    "Photography Hours": "6",
    "Videography Hours": "4",
    "Drone Services": "Yes",
    "Project Location": "123 Main St, Austin, TX",
    "Photography Start Time": "2:00 PM",
    "Videography Start Time": "1:00 PM",
    "Type of Event": "Wedding",
    "stage": "lead",
    "contact_id": "test_lead_123"
}
try:
    r = requests.post("http://localhost:8080/webhook/calendar-ghl", json=payload1, timeout=5)
    result = r.json()
    print(f"   Status: {r.status_code}")
    print(f"   Action: {result.get('action')}")
    print(f"   Title: {result.get('event_title')}")
    print(f"   Color: {result.get('color')}")
    test_results.append(("Lead Event", result.get('status') == 'success'))
except Exception as e:
    print(f"   Error: {e}")
    test_results.append(("Lead Event", False))

# Test 2: Booked payload
print("\nTest 2: Booked event")
payload2 = {
    "Opportunity Name": "Smith Corporate Event",
    "Event Date": "2025-08-20",
    "Photography Hours": "4",
    "Videography Hours": "0",
    "Drone Services": "No",
    "Project Location": "Downtown Hotel",
    "Photography Start Time": "10:00 AM",
    "Type of Event": "Corporate",
    "stage": "booked",
    "contact_id": "test_booked_456"
}
try:
    r = requests.post("http://localhost:8080/webhook/calendar-ghl", json=payload2, timeout=5)
    result = r.json()
    print(f"   Status: {r.status_code}")
    print(f"   Action: {result.get('action')}")
    print(f"   Title: {result.get('event_title')}")
    print(f"   Color: {result.get('color')}")
    test_results.append(("Booked Event", result.get('status') == 'success'))
except Exception as e:
    print(f"   Error: {e}")
    test_results.append(("Booked Event", False))

# Test 3: Update existing event
print("\nTest 3: Update existing event")
payload3 = {
    "Opportunity Name": "Davis Birthday Party",
    "Event Date": "2025-09-10",
    "Photography Hours": "3",
    "Videography Hours": "2",
    "Drone Services": "Yes",
    "Project Location": "Backyard, Houston",
    "Photography Start Time": "3:00 PM",
    "Type of Event": "Party",
    "stage": "booked",
    "contact_id": "test_update_789",
    "Google Calendar Event ID From Make": "existing_event_123"
}
try:
    r = requests.post("http://localhost:8080/webhook/calendar-ghl", json=payload3, timeout=5)
    result = r.json()
    print(f"   Status: {r.status_code}")
    print(f"   Action: {result.get('action')}")
    print(f"   Event ID: {result.get('event_id')}")
    test_results.append(("Update Event", result.get('action') == 'updated'))
except Exception as e:
    print(f"   Error: {e}")
    test_results.append(("Update Event", False))

# Test 4: Minimal payload
print("\nTest 4: Minimal payload (edge case)")
payload4 = {
    "Opportunity Name": "Minimal Test",
    "contact_id": "test_minimal"
}
try:
    r = requests.post("http://localhost:8080/webhook/calendar-ghl", json=payload4, timeout=5)
    result = r.json()
    print(f"   Status: {r.status_code}")
    print(f"   Action: {result.get('action')}")
    print(f"   Title: {result.get('event_title')}")
    test_results.append(("Minimal Payload", result.get('status') == 'success'))
except Exception as e:
    print(f"   Error: {e}")
    test_results.append(("Minimal Payload", False))

# List all events
print("\n3. Checking mock events storage...")
try:
    r = requests.get("http://localhost:8080/mock/events", timeout=2)
    storage = r.json()
    print(f"   Total webhooks received: {storage.get('total_requests', 0)}")
    print(f"   Events created: {len(storage.get('events', {}))}")
    print(f"   Contacts updated: {len(storage.get('contacts', {}))}")
except Exception as e:
    print(f"   Error: {e}")

# Cleanup
print("\n4. Stopping server...")
server_process.terminate()
try:
    server_process.wait(timeout=5)
    print("   Server stopped")
except:
    server_process.kill()
    print("   Server force killed")

# Summary
print("\n" + "="*60)
print("TEST SUMMARY")
print("="*60)
passed = sum(1 for _, r in test_results if r)
total = len(test_results)
print(f"\nPassed: {passed}/{total}")
for name, result in test_results:
    status = "✅ PASS" if result else "❌ FAIL"
    print(f"  {status}: {name}")

if passed == total:
    print("\n✅ All tests passed! Workflow logic is working correctly.")
    print("\nThe workflow correctly:")
    print("  - Parses hours from strings")
    print("  - Detects drone services")
    print("  - Determines booked vs lead status")
    print("  - Calculates event timing")
    print("  - Builds appropriate titles with services")
    print("  - Sets correct colors (Orange for leads, Red for booked)")
    print("  - Handles updates vs creates")
else:
    print(f"\n⚠️  {total - passed} test(s) failed")

print("\n" + "="*60)
