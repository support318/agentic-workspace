# API Mappings Documentation

This document catalogs all API integrations migrated from n8n to the DO framework.

## GoHighLevel (LeadConnector) API

### Base URL
```
https://services.leadconnectorhq.com
```

### Authentication
- **Type**: Bearer Token
- **Header**: `Authorization: Bearer {token}`
- **Version Header**: `Version: 2021-07-28`
- **Current Token**: `pit-77fd8ed2-a17f-4b90-b4dc-5510aad2ebdf` (may need refresh)
- **Updated Token**: `pit-10e989e3-51b5-4787-bccb-f12d284eda13` (from n8n)

### Endpoints Used

| Operation | Method | Endpoint | Purpose |
|-----------|--------|----------|---------|
| Get Contact | GET | `/contacts/{contactId}` | Fetch contact details |
| Update Contact | PUT | `/contacts/{contactId}` | Update contact with custom fields |
| Search Contacts | GET | `/contacts?query={search}` | Search by name/email/phone |
| Get Opportunity | GET | `/opportunities/{opportunityId}` | Fetch opportunity details |
| List Opportunities | GET | `/opportunities?pipelineId={id}` | Get all in pipeline |

### Custom Fields
| Field Key | Description |
|-----------|-------------|
| `google_calendar_event_id_from_make` | Stores Google Calendar event ID for back-reference |

### Data Flow from n8n

**n8n Node "Update GHL with Event ID":**
```
PUT https://services.leadconnectorhq.com/contacts/{contactId}
Headers:
  Authorization: Bearer {token}
  Accept: application/json
  Version: 2021-07-28
  Content-Type: application/json

Body:
{
  "customFields": [
    {
      "key": "google_calendar_event_id_from_make",
      "field_value": "{calendar_event_id}"
    }
  ]
}
```

## Google Calendar API

### Base URL
```
https://www.googleapis.com/calendar/v3
```

### Authentication
- **Type**: OAuth2
- **Scopes**: `https://www.googleapis.com/auth/calendar`
- **Calendar ID**: `support@candidstudios.net`
- **Credential ID in n8n**: `NJx0Gc7LBELuqFkH`

### Color IDs
| ID | Color | Usage |
|----|-------|-------|
| 1 | Blue | Default |
| 6 | Orange/Tangerine | Lead events |
| 11 | Red | Booked events |

### Endpoints Used

| Operation | Method | Endpoint | Purpose |
|-----------|--------|----------|---------|
| Create Event | POST | `/calendars/{calendarId}/events` | Create new event |
| Update Event | PUT | `/calendars/{calendarId}/events/{eventId}` | Update existing event |
| Get Event | GET | `/calendars/{calendarId}/events/{eventId}` | Fetch event details |
| List Events | GET | `/calendars/{calendarId}/events` | List events in range |

### Data Flow from n8n

**n8n Node "Create Calendar Event":**
```
POST https://www.googleapis.com/calendar/v3/calendars/support@candidstudios.net/events
Body:
{
  "summary": "{eventTitle}",
  "description": "{eventDescription}",
  "location": "{location}",
  "start": {
    "dateTime": "{startDatetime}",
    "timeZone": "America/New_York"
  },
  "end": {
    "dateTime": "{endDatetime}",
    "timeZone": "America/New_York"
  },
  "colorId": "{6 or 11}",
  "sendUpdates": "all",
  "visibility": "default"
}
```

**n8n Node "Update Calendar Event":**
```
PUT https://www.googleapis.com/calendar/v3/calendars/support@candidstudios.net/events/{eventId}
Body: (same as create, plus eventId)
```

## Keycloak API

### Base URL
```
https://login.candidstudios.net/admin
```

### Authentication
- **Admin Console**: `https://login.candidstudios.net/admin`
- **Realm**: Default realm for notes.candidstudios.net
- **Existing MCP Server**: `C:/Users/ryanm/keycloak-mcp-server/`

### Integration Strategy
- Reuse existing `keycloak-mcp-server` if possible
- Or create direct Python wrapper using `python-keycloak` library

## Webhook Infrastructure

### n8n Webhook (being replaced)
- **Endpoint**: `calendar-event-ghl`
- **URL**: `https://{n8n-host}/webhook/calendar-event-ghl`
- **Method**: POST

### New Flask Webhook
- **Endpoint**: `/webhook/calendar-ghl`
- **URL**: `https://candidstudios.net/webhook/calendar-ghl` (after deployment)
- **Method**: POST
- **Port**: 8080 (default)

## Data Transformation

### n8n Code → Python Functions

| n8n Function | Python Equivalent |
|--------------|-------------------|
| `parseHours(str)` | `parse_hours(value)` in `webhook_server.py` |
| `parseTimeStr(timeStr)` | `parse_time_str(time_str)` in `webhook_server.py` |
| Webhook data parsing | Direct dict access in Flask |
| Event title building | `create_ghl_event()` in `google_calendar.py` |
| Description building | `create_ghl_event()` in `google_calendar.py` |

## Environment Variables Required

```bash
# GoHighLevel
GHL_API_TOKEN=pit-77fd8ed2-a17f-4b90-b4dc-5510aad2ebdf
GHL_LOCATION_ID=

# Google Calendar
GOOGLE_CALENDAR_ID=support@candidstudios.net
GOOGLE_CREDENTIALS_PATH=/path/to/credentials.json

# Webhook Server
PORT=8080
DEBUG=False
WEBHOOK_SECRET=
ALLOWED_IPS=127.0.0.1,webhook.gohighlevel.com
```

## Migration Checklist

- [x] Create GHL API wrapper (`ghl_api.py`)
- [x] Create Google Calendar wrapper (`google_calendar.py`)
- [x] Create Flask webhook server (`webhook_server.py`)
- [x] Create directive for workflow (`ghl_calendar_sync.md`)
- [x] Create test suite
- [x] Create deployment script
- [ ] Set up Google OAuth credentials on server
- [ ] Get fresh GHL API token if needed
- [ ] Deploy to server
- [ ] Configure GoHighLevel webhook to new endpoint
- [ ] Run shadow deployment alongside n8n
- [ ] Verify all functionality working
- [ ] Switch DNS/webhook routing
- [ ] Monitor for 1 week before decommissioning n8n
