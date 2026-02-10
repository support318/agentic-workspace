# Agentic Workspace - DO Framework

Replace n8n visual workflows with natural language directives and deterministic execution scripts.

## Overview

This workspace implements the **DO (Directive Orchestration Execution)** framework for migrating from n8n to AI-powered agentic workflows.

### What's Migrated

| Workflow | Status | Description |
|----------|--------|-------------|
| GHL Calendar Sync | ✅ Complete | Sync GoHighLevel opportunities to Google Calendar |
| Wedding Lead Scraper | ✅ Existing | Scrape wedding vendor leads |
| Email Outreach | ✅ Existing | Send email campaigns |

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API credentials

# Run tests
pytest

# Start webhook server
python execution/webhook_server.py
```

### Deployment to Server

```bash
# Deploy to production server
bash scripts/deploy.sh

# SSH to server
ssh candid@192.168.40.100

# Start service
sudo systemctl start agentic-webhooks

# Check logs
sudo journalctl -u agentic-webhooks -f
```

## Project Structure

```
agentic-workspace/
├── agents.md              # DO framework system prompt
├── .env.example           # Environment template
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── API_MAPPINGS.md       # API documentation
│
├── directives/           # WHAT to do (natural language)
│   ├── ghl_calendar_sync.md       # GHL → Google Calendar
│   ├── scrape_wedding_leads.md    # Lead scraping
│   └── send_outreach_email.md     # Email campaigns
│
├── execution/            # HOW to do it (Python scripts)
│   ├── ghl_api.py               # GoHighLevel API wrapper
│   ├── google_calendar.py       # Google Calendar wrapper
│   ├── webhook_server.py        # Flask webhook receiver
│   ├── send_email_smtp.py       # Email sender
│   ├── upload_to_sheets.py      # Google Sheets uploader
│   └── web_search.py            # Web search utilities
│
├── tests/                # Test suite
│   ├── conftest.py              # Pytest fixtures
│   └── integration/
│       ├── test_ghl_api.py      # GHL API tests
│       ├── test_calendar.py     # Calendar tests
│       ├── test_webhook_server.py # Webhook tests
│       └── test_full_workflow.py # End-to-end tests
│
├── services/             # Systemd service files
│   └── agentic-webhooks.service
│
└── scripts/              # Deployment scripts
    └── deploy.sh
```

## Webhook Endpoints

Once deployed, the webhook server exposes:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/webhook/calendar-ghl` | POST | GHL calendar sync |
| `/webhook/lead-created` | POST | New lead notifications |
| `/webhook/contact-updated` | POST | Contact updates |
| `/health` | GET | Health check |

## Configuration

### Required Environment Variables

Create a `.env` file with:

```bash
# GoHighLevel
GHL_API_TOKEN=your_token_here
GHL_LOCATION_ID=your_location_id

# Google Calendar
GOOGLE_CALENDAR_ID=support@candidstudios.net
GOOGLE_CREDENTIALS_PATH=/path/to/credentials.json

# Webhook Server
PORT=8080
DEBUG=False
WEBHOOK_SECRET=your_secret_here
ALLOWED_IPS=127.0.0.1,webhook.gohighlevel.com
```

### Google Calendar OAuth Setup

1. Go to Google Cloud Console
2. Create OAuth 2.0 credentials (Desktop app)
3. Download credentials JSON
4. Set path in `.env`

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=execution

# Run specific test file
pytest tests/integration/test_ghl_api.py

# Run specific test
pytest tests/integration/test_ghl_api.py::TestGoHighLevelAPI::test_get_contact
```

## Monitoring

### Check Service Status
```bash
sudo systemctl status agentic-webhooks
```

### View Logs
```bash
# Real-time logs
sudo journalctl -u agentic-webhooks -f

# Last 100 lines
sudo journalctl -u agentic-webhooks -n 100

# Since today
sudo journalctl -u agentic-webhooks --since today
```

### Restart Service
```bash
sudo systemctl restart agentic-webhooks
```

## Troubleshooting

### Port Already in Use
```bash
# Check what's using port 8080
sudo lsof -i :8080

# Kill the process
sudo kill <PID>
```

### Import Errors
```bash
# Reinstall dependencies
source venv/bin/activate
pip install -r requirements.txt
```

### GHL API Token Expired
Update token in `.env` and restart service:
```bash
sudo systemctl restart agentic-webhooks
```

## Development Notes

### Adding a New Workflow

1. Create directive in `directives/new_workflow.md`
2. Create execution script in `execution/new_script.py`
3. Add tests in `tests/`
4. Update `requirements.txt` if needed
5. Deploy and test

### Code Style

- Use type hints where appropriate
- Include docstrings for functions
- Handle errors gracefully
- Log important events

## License

Proprietary - Candid Studios

## Support

For issues or questions, contact the development team.
