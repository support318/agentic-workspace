# GHL Calendar Sync Directive

## Objective
Synchronize GoHighLevel opportunity data to Google Calendar when events are created or updated. This replaces the n8n "Calendar Event Created/Updated from GHL" workflow.

## Inputs
This workflow is triggered by a webhook from GoHighLevel with the following payload:

```json
{
  "Opportunity Name": "Johnson Wedding - Photography & Video",
  "Event Date": "2025-06-15",
  "Photography Hours": "6",
  "Videography Hours": "4",
  "Drone Services": "Yes",
  "Project Location": "123 Main St, City, State",
  "Secondary Location": "Reception Hall",
  "Photography Start Time": "2:00 PM",
  "Videography Start Time": "1:00 PM",
  "Assigned Photographer": "John Smith",
  "Assigned Videographer": "Jane Doe",
  "Type of Event": "Wedding",
  "stage": "booked",
  "contact_id": "abc123xyz",
  "Calendar Event ID": "",
  "Google Calendar Event ID From Make": ""
}
```

## Process

### 1. Receive Webhook
- Endpoint: `/webhook/calendar-ghl`
- Validate webhook signature (if configured)
- Parse JSON payload

### 2. Parse and Normalize Data
- Extract photography hours (parse "6 hours" → 6)
- Extract videography hours (parse "4 hours" → 4)
- Determine event duration: max(photo_hours, video_hours, 4)
- Parse start times to find earliest start
- Check if drone services are included (yes/true/y)
- Determine if booked (stage == "booked")

### 3. Determine Action
- If `Calendar Event ID` or `Google Calendar Event ID From Make` exists: **Update** existing event
- Otherwise: **Create** new event

### 4. Build Calendar Event
Use `execution/google_calendar.py` to create/update event with:

**Title Format:**
```
{Opportunity Name} - [Photo/Video/Drone] (Lead)
```
- Don't add "(Lead)" if stage is "booked"

**Description (HTML with `<br>` line breaks):**
```
🎉 Type of Event: {Type of Event}
📸 Photography Hours: {Photography Hours}
🎬 Videography Hours: {Videography Hours}
🚁 Drone Services: {Drone Services}
📍 Project Location: {Project Location}
📍 Secondary Location: {Secondary Location}
👨‍💼 Assigned Photographer: {Assigned Photographer}
👨‍💼 Assigned Videographer: {Assigned Videographer}
⏰ Photography Start Time: {Photography Start Time}
⏰ Videography Start Time: {Videography Start Time}
```

**Event Timing:**
- Start: Earlier of photography/videography start time on event date
- End: Start time + max_hours duration
- Timezone: America/New_York

**Color ID:**
- Booked events: `11` (Red)
- Lead events: `6` (Orange)

### 5. Update GoHighLevel Contact
- Use `execution/ghl_api.py` to update the contact
- Set custom field `google_calendar_event_id_from_make` to the new/updated calendar event ID
- This creates a back-reference for future updates

### 6. Return Response
Return JSON with:
```json
{
  "status": "success",
  "action": "created" | "updated",
  "event_id": "google_calendar_event_id",
  "event_title": "Event title",
  "event_start": {
    "dateTime": "2025-06-15T13:00:00"
  },
  "is_booked": true
}
```

## Tools Available
- `execution/ghl_api.py`: GoHighLevel API wrapper
  - `get_contact(contact_id)` - Fetch contact data
  - `update_contact_calendar_event_id(contact_id, event_id)` - Update contact
- `execution/google_calendar.py`: Google Calendar API wrapper
  - `create_event(...)` - Create new event
  - `update_event(event_id, ...)` - Update existing event
- `execution/webhook_server.py`: Flask webhook receiver

## Definition of Done
- [ ] Webhook received and validated
- [ ] Calendar event created or updated with correct title, description, timing
- [ ] Color ID set correctly (booked vs lead)
- [ ] GHL contact updated with calendar event ID
- [ ] Success response returned
- [ ] Error logged and appropriate response returned if something fails

## Edge Cases
- **Missing event date**: Use today's date
- **Missing hours**: Default to 4 hours minimum
- **Missing start time**: Default to 10:00 AM
- **GHL update fails**: Log error but don't fail the webhook (calendar already created)
- **Calendar API error**: Return 500 error with details
- **Invalid date format**: Try to parse, return 400 if fails

## Timezone Handling
All events use `America/New_York` timezone. When parsing dates from GHL:
- If date only: "2025-06-15" → treat as all-day (not currently used, we use times)
- If datetime: "2025-06-15T14:00:00" → use directly
- When calculating end time: Add hours to start datetime

## Testing
Send test webhook payload:
```bash
curl -X POST http://localhost:8080/webhook/calendar-ghl \
  -H "Content-Type: application/json" \
  -d '{
    "Opportunity Name": "Test Wedding",
    "Event Date": "2025-07-15",
    "Photography Hours": "6",
    "Videography Hours": "0",
    "stage": "booked",
    "contact_id": "test123"
  }'
```

## Dependencies
- `flask>=2.3.0` - Web server
- `requests>=2.31.0` - HTTP client for GHL API
- `google-api-python-client>=2.100.0` - Google Calendar API
- `google-auth-oauthlib>=1.0.0` - OAuth for Google
- `python-dotenv>=1.0.0` - Environment variables
