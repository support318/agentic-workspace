# Scrape Wedding Leads

## Objective
Scrape leads from wedding-related venues and vendors in a specified location. This workflow finds potential wedding business clients who may need marketing/automation services.

## Inputs
- `location` (required): City, region, or geographic area to search
- `vendor_types` (optional): Types of wedding vendors to search. Default: ["venues", "photographers", "caterers", "planners"]
- `limit` (optional): Maximum number of leads to return. Default: 50

## Process

1. **Search Discovery**
   - Use web search to find wedding vendor directories and listings for the specified location
   - Target sites may include:
     - WeddingWire
     - The Knot
     - Wedding.com
     - Local business directories
     - Google Maps business listings

2. **Lead Extraction**
   - For each vendor found, extract:
     - Business name
     - Contact email (primary)
     - Phone number (if available)
     - Website URL
     - Vendor type/category
     - Location (city, state)

3. **Data Enrichment**
   - Visit each website to find:
     - Additional contact emails (info@, contact@, etc.)
     - Social media links
     - Business description/keywords
     - Wedding package pricing (if listed)

4. **Quality Filtering**
   - Exclude leads that:
     - Have no email address
     - Are outside the target location (more than 50 miles)
     - Are large chains/corporations (focus on local businesses)

5. **Output Generation**
   - Save results to Google Sheet with format:
     - Date scraped | Business Name | Email | Phone | Website | Vendor Type | Location | Notes
   - Return the Google Sheet URL to user

## Tools Available
- `execution/web_search.py`: Search the web for vendor listings
- `execution/scrape_google_maps.py`: Scrape Google Maps for local businesses
- `execution/visit_website.py`: Extract contact info from websites
- `execution/upload_to_sheets.py`: Upload results to Google Sheets

## Definition of Done
- Google Sheet created with at least `limit` valid leads
- Each lead has a verified email address
- All leads are within the specified location
- Sheet URL provided to user
- Summary report including: total leads found, lead types breakdown

## Edge Cases
- **No emails found**: Expand search to social media profiles
- **Rate limiting**: Implement delays between requests (2-5 seconds)
- **Blocked scraping**: Switch to alternative data sources
- **Duplicate leads**: Deduplicate by email domain

## Example Usage
```
scrape_wedding_leads --location "Austin, Texas" --vendor_types ["venues", "photographers"] --limit 30
```

## Notes
- Focus on small-to-medium local businesses (good candidates for services)
- Wedding venues often have event coordinator contacts - prioritize these
- Photographers and planners often book multiple weddings - good for outreach
