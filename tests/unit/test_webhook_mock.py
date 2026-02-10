"""
Test the webhook workflow by sending mock requests.
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
import json
import time

# Server URL
BASE_URL = "http://localhost:8080"


def test_health():
    """Test health endpoint."""
    print("\n1. Testing /health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        return True
    except Exception as e:
        print(f"   Error: {e}")
        return False


def test_webhook_lead():
    """Test webhook with lead payload."""
    print("\n2. Testing webhook with LEAD payload...")

    payload = {
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
        response = requests.post(
            f"{BASE_URL}/webhook/calendar-ghl",
            json=payload,
            timeout=5
        )
        print(f"   Status: {response.status_code}")
        result = response.json()
        print(f"   Action: {result.get('action')}")
        print(f"   Event ID: {result.get('event_id')}")
        print(f"   Title: {result.get('event_title')}")
        print(f"   Color: {result.get('color')}")
        return result.get('status') == 'success'
    except Exception as e:
        print(f"   Error: {e}")
        return False


def test_webhook_booked():
    """Test webhook with booked payload."""
    print("\n3. Testing webhook with BOOKED payload...")

    payload = {
        "Opportunity Name": "Smith Corporate Event",
        "Event Date": "2025-08-20",
        "Photography Hours": "4",
        "Videography Hours": "0",
        "Drone Services": "No",
        "Project Location": "Downtown Hotel, Dallas, TX",
        "Photography Start Time": "10:00 AM",
        "Type of Event": "Corporate",
        "stage": "booked",
        "contact_id": "test_booked_456"
    }

    try:
        response = requests.post(
            f"{BASE_URL}/webhook/calendar-ghl",
            json=payload,
            timeout=5
        )
        print(f"   Status: {response.status_code}")
        result = response.json()
        print(f"   Action: {result.get('action')}")
        print(f"   Event ID: {result.get('event_id')}")
        print(f"   Title: {result.get('event_title')}")
        print(f"   Color: {result.get('color')}")
        return result.get('status') == 'success'
    except Exception as e:
        print(f"   Error: {e}")
        return False


def test_webhook_update():
    """Test webhook with existing event ID (update scenario)."""
    print("\n4. Testing webhook with EXISTING EVENT (update)...")

    payload = {
        "Opportunity Name": "Davis Birthday Party",
        "Event Date": "2025-09-10",
        "Photography Hours": "3",
        "Videography Hours": "2",
        "Drone Services": "Yes",
        "Project Location": "Backyard, Houston, TX",
        "Photography Start Time": "3:00 PM",
        "Type of Event": "Party",
        "stage": "booked",
        "contact_id": "test_update_789",
        "Google Calendar Event ID From Make": "existing_cal_event_123"
    }

    try:
        response = requests.post(
            f"{BASE_URL}/webhook/calendar-ghl",
            json=payload,
            timeout=5
        )
        print(f"   Status: {response.status_code}")
        result = response.json()
        print(f"   Action: {result.get('action')}")
        print(f"   Event ID: {result.get('event_id')}")
        print(f"   Title: {result.get('event_title')}")
        print(f"   Color: {result.get('color')}")
        return result.get('action') == 'updated'
    except Exception as e:
        print(f"   Error: {e}")
        return False


def test_webhook_minimal():
    """Test webhook with minimal payload (edge case)."""
    print("\n5. Testing webhook with MINIMAL payload...")

    payload = {
        "Opportunity Name": "Minimal Test Event",
        "contact_id": "test_minimal_001"
    }

    try:
        response = requests.post(
            f"{BASE_URL}/webhook/calendar-ghl",
            json=payload,
            timeout=5
        )
        print(f"   Status: {response.status_code}")
        result = response.json()
        print(f"   Action: {result.get('action')}")
        print(f"   Title: {result.get('event_title')}")
        return result.get('status') == 'success'
    except Exception as e:
        print(f"   Error: {e}")
        return False


def test_list_events():
    """List all mock events created."""
    print("\n6. Listing all mock events created...")
    try:
        response = requests.get(f"{BASE_URL}/mock/events", timeout=2)
        print(f"   Status: {response.status_code}")
        result = response.json()
        print(f"   Total Requests: {result.get('total_requests', 0)}")
        print(f"   Events Created: {len(result.get('events', {}))}")
        print(f"   Contacts Updated: {len(result.get('contacts', {}))}")
        return True
    except Exception as e:
        print(f"   Error: {e}")
        return False


if __name__ == "__main__":
    print("="*60)
    print("WEBHOOK TESTING - Make sure mock server is running!")
    print("Run: python scripts/test_local_server.py")
    print("="*60)

    # Check if server is running
    try:
        requests.get(BASE_URL, timeout=1)
    except:
        print("\n❌ Server not running! Start it first:")
        print("   python scripts/test_local_server.py")
        sys.exit(1)

    # Run tests
    results = []
    results.append(("Health Check", test_health()))
    results.append(("Lead Payload", test_webhook_lead()))
    results.append(("Booked Payload", test_webhook_booked()))
    results.append(("Update Payload", test_webhook_update()))
    results.append(("Minimal Payload", test_webhook_minimal()))
    results.append(("List Events", test_list_events()))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    passed = sum(1 for _, r in results if r)
    total = len(results)
    print(f"\nPassed: {passed}/{total}")
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")

    if passed == total:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")

    print("="*60)
