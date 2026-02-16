# SimplyNoted Thank You Cards Directive

## Objective
Automatically send handwritten thank you cards via SimplyNoted to clients the day after their event. Cards are personalized based on event type (wedding, bar/bat mitzvah, quinceañera, corporate). This replaces the n8n workflow at `n8n.candidstudios.net/webhook/simplynoted`.

## Inputs
Triggered by a webhook POST from GoHighLevel with contact data:

```json
{
  "first_name": "Jessica",
  "last_name": "Martinez",
  "Partner's First Name": "David",
  "Type of Event": "Wedding",
  "Event Date": "2026-03-15",
  "address1": "123 Main St",
  "address2": "Apt 4B",
  "city": "Miami",
  "state": "FL",
  "postalCode": "33101"
}
```

### Required Fields
- `first_name` - Client's first name
- `Type of Event` - Event type for routing (wedding, bar mitzvah, bat mitzvah, quinceañera, corporate, event, commercial event)
- `address1`, `city`, `state`, `postalCode` - Mailing address

### Optional Fields
- `last_name` - Client's last name
- `Partner's First Name` - Partner name (used in wedding messages)
- `Event Date` - Date of event (YYYY-MM-DD). If missing, defaults to today.
- `address2` - Address line 2

## Process

### 1. Receive Webhook
- Endpoint: `/webhook/simplynoted-thank-you`
- Parse JSON payload from GHL

### 2. Route by Event Type
Determine which card and message to use based on `Type of Event`:

| Event Type | Card ID | Message Template |
|---|---|---|
| Wedding | `SIMPLYNOTED_CARD_WEDDING` | Wedding message (includes partner name) |
| Quinceañera / Quinceanera | `SIMPLYNOTED_CARD_QUINCE` | Quinceañera message |
| Bar Mitzvah / Bat Mitzvah | `SIMPLYNOTED_CARD_DEFAULT` | Bar/Bat Mitzvah message |
| Corporate / Event / Commercial | `SIMPLYNOTED_CARD_DEFAULT` | Corporate message |

### 3. Message Templates

**Wedding:**
```
Dear {first_name} & {partner_name},

Thank you for allowing us to be part of your special day! It was an absolute pleasure capturing all the beautiful moments of your wedding. We can't wait for you to see the final result.

Warm regards,
The Candid Studios Team
```

**Bar/Bat Mitzvah:**
```
Dear {first_name},

Congratulations on your {event_type}! It was such an honor to be part of this milestone celebration. We loved capturing every special moment and can't wait for you to relive them.

Warm regards,
The Candid Studios Team
```

**Quinceañera:**
```
Dear {first_name},

What a beautiful celebration of your daughter's quinceañera! Thank you for trusting us to capture these precious memories. It was truly a magical evening and we're honored to have been part of it.

Warm regards,
The Candid Studios Team
```

**Corporate/Default:**
```
Dear {first_name},

Thank you for choosing to work with us for your event. It was a pleasure providing our services and we hope the results exceed your expectations. We look forward to working together again!

Warm regards,
The Candid Studios Team
```

### 4. Calculate Shipping Date
- Parse `Event Date` field
- Add 1 day (card ships the day after the event)
- If no event date provided, use tomorrow's date
- Format as `YYYY-MM-DD`

### 5. Build Recipient Data
```json
{
  "name": "{first_name} {last_name}",
  "address1": "{address1}",
  "address2": "{address2}",
  "city": "{city}",
  "state": "{state}",
  "zip": "{postalCode}",
  "country": "US"
}
```

### 6. Send via SimplyNoted API
- POST to `https://api.simplynoted.com/api/orders`
- Auth: Bearer token from `SIMPLYNOTED_API_KEY`
- Return address: Candid Studios, 210 174th St Unit 705, Sunny Isles Beach FL 33160
- Handwriting style: Nemo

## Edge Cases
- Missing partner name for weddings: Use just the client's first name ("Dear Jessica,")
- Missing event date: Ship tomorrow
- Missing address fields: Return 400 error with details
- Unrecognized event type: Use default card and corporate message
- SimplyNoted API error: Log error, return 500 with details

## Environment Variables
- `SIMPLYNOTED_API_KEY` - API authentication key
- `SIMPLYNOTED_USER_ID` - SimplyNoted user ID
- `SIMPLYNOTED_CARD_WEDDING` - Card product ID for weddings
- `SIMPLYNOTED_CARD_QUINCE` - Card product ID for quinceañeras
- `SIMPLYNOTED_CARD_DEFAULT` - Card product ID for all other events

## GHL Webhook Configuration
The GHL workflow should POST to: `https://webhook.candidstudios.net/webhook/simplynoted-thank-you`
(Previously: `https://n8n.candidstudios.net/webhook/simplynoted`)

