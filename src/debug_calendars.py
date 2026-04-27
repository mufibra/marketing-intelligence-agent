"""Debug: try different parameter combos for calendar events"""
from ghl_fetcher import _get, GHL_LOCATION_ID
from datetime import datetime, timedelta

cal_id = "eSmhKBmhnDHmj3BkkVBg"  # Charmain's 45 Min Calendar
cal_name = "Charmain's 45 Min Calendar"

start_iso = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%dT00:00:00Z")
end_iso = datetime.now().strftime("%Y-%m-%dT23:59:59Z")
start_epoch = int((datetime.now() - timedelta(days=365)).timestamp() * 1000)
end_epoch = int(datetime.now().timestamp() * 1000)

print(f"Testing calendar: {cal_name}")
print(f"ID: {cal_id}")
print()

# Test 1: Current approach
print("Test 1: locationId + calendarId + startTime + endTime (ISO)")
data = _get("/calendars/events", {
    "locationId": GHL_LOCATION_ID,
    "calendarId": cal_id,
    "startTime": start_iso,
    "endTime": end_iso,
})
print(f"  Result: {len(data.get('events', []))} events" if data else "  Result: None")
print()

# Test 2: Without calendarId (all calendars)
print("Test 2: locationId + startTime + endTime (no calendarId)")
data = _get("/calendars/events", {
    "locationId": GHL_LOCATION_ID,
    "startTime": start_iso,
    "endTime": end_iso,
})
print(f"  Result: {len(data.get('events', []))} events" if data else "  Result: None")
print()

# Test 3: Epoch timestamps
print("Test 3: locationId + calendarId + startTime + endTime (epoch ms)")
data = _get("/calendars/events", {
    "locationId": GHL_LOCATION_ID,
    "calendarId": cal_id,
    "startTime": start_epoch,
    "endTime": end_epoch,
})
print(f"  Result: {len(data.get('events', []))} events" if data else "  Result: None")
print()

# Test 4: Different path with calendar ID in URL
print("Test 4: /calendars/{calendarId}/events")
data = _get(f"/calendars/{cal_id}/events", {
    "locationId": GHL_LOCATION_ID,
    "startTime": start_iso,
    "endTime": end_iso,
})
print(f"  Result: {len(data.get('events', []))} events" if data else "  Result: None")
print()

# Test 5: No date filter at all
print("Test 5: locationId + calendarId only (no date)")
data = _get("/calendars/events", {
    "locationId": GHL_LOCATION_ID,
    "calendarId": cal_id,
})
print(f"  Result: {len(data.get('events', []))} events" if data else "  Result: None")
if data:
    print(f"  Keys: {list(data.keys())}")
    print(f"  Preview: {str(data)[:300]}")
print()

# Test 6: Try /calendars/events/appointments
print("Test 6: /calendars/events with userId param")
data = _get("/calendars/events", {
    "locationId": GHL_LOCATION_ID,
    "startTime": start_iso,
    "endTime": end_iso,
    "calendarId": cal_id,
    "includeAll": True,
})
print(f"  Result: {len(data.get('events', []))} events" if data else "  Result: None")
