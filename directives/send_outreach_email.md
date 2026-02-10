# Send Outreach Email

## Objective
Send personalized outreach emails to a list of leads. This workflow is designed for B2B outreach to offer services.

## Inputs
- `leads_file` (required): Path to CSV or Google Sheet with leads
  - Required columns: `email`, `business_name`
  - Optional columns: `first_name`, `business_type`, `location`
- `template` (required): Email template to use. Options:
  - `wedding_intro`: Introduction email for wedding vendors
  - `automation_services`: Offer automation/AI services
  - `lead_generation`: Offer lead generation services
  - `custom`: User-provided template
- `sender_name` (optional): Your name. Default: From .env or config
- `schedule_time` (optional): When to send. Default: immediately

## Process

1. **Load Leads**
   - Read from CSV file or Google Sheet
   - Validate that all leads have required fields (email, business_name)
   - Skip leads with invalid or missing emails

2. **Personalize Each Email**
   - Use template to generate personalized email
   - Include:
     - Recipient's business name
     - Recipient's first name (if known)
     - Location-specific context
     - Relevant pain points based on business type
     - Clear call-to-action

3. **Send via SMTP**
   - Use configured SMTP server (Gmail recommended)
   - Rate limit: 30 emails per hour, max 100 per day
   - Add delays between sends (2-5 seconds)

4. **Tracking & Reporting**
   - Log each send with timestamp
   - Track: sent, failed, bounced
   - Generate report with:
     - Total emails sent
     - Success rate
     - Failed emails with reasons

## Tools Available
- `execution/send_email_smtp.py`: Send individual email via SMTP
- `execution/load_leads.py`: Load leads from file/sheet
- `execution/validate_email.py`: Validate email format
- `execution/log_send.py`: Log send results

## Email Templates

### wedding_intro
Subject: Quick question about [business_name]

Hi [first_name or team],

I came across [business_name] while browsing wedding vendors in [location], and I wanted to reach out.

I help businesses like yours with [specific value prop - e.g., streamlining booking inquiries, automated follow-ups, etc.].

Would you be open to a brief 15-minute call to discuss how we might be able to [specific benefit]?

No pressure - just exploring potential partnerships.

Best,
[sender_name]

### automation_services
Subject: Save 10+ hours/week on [specific task]

Hi [first_name],

I noticed [specific observation about their business/site].

I recently helped [similar business] reduce [specific pain point] by 80% using automated workflows.

Would you be interested in seeing how this could work for [business_name]?

Happy to share a free audit of your current process.

Best regards,
[sender_name]

## Definition of Done
- All valid leads sent personalized email
- Send log created with full tracking
- Summary report generated
- No emails sent to invalid addresses

## Edge Cases
- **SMTP quota exceeded**: Schedule remaining sends for next day
- **Invalid email**: Log and skip, don't send
- **Missing first_name**: Use "team" or business name
- **Send failure**: Retry once, then log as failed

## Safety Limits
- Maximum: 100 emails per day
- Rate: 1 email per 3 seconds minimum
- Stop after 3 consecutive failures
- Always use BCC for bulk sends (if supported)

## Configuration Required
Before first use, ensure `.env` has:
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_APP_PASSWORD=your_app_password
```

Get app password: https://support.google.com/accounts/answer/185833
