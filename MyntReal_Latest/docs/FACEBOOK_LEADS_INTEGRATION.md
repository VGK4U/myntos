# Facebook Lead Ads Integration Setup Guide

## Overview
This integration automatically captures leads from Facebook Lead Ads campaigns and creates entries in the CRM module with proper field mapping.

## Requirements
1. Facebook Business Account with Page Admin access
2. Facebook App with Lead Ads permissions
3. Published and deployed webhook URL (HTTPS required)

## Environment Secrets Required

| Secret Name | Description |
|-------------|-------------|
| `FACEBOOK_APP_SECRET` | Your Facebook App's secret key (from Facebook Developer Console) |
| `FACEBOOK_PAGE_ACCESS_TOKEN` | Page Access Token with `leads_retrieval` and `pages_manage_ads` permissions |
| `FACEBOOK_WEBHOOK_VERIFY_TOKEN` | A custom token you create for webhook verification (any secure random string) |

## Facebook Developer Console Setup

### Step 1: Create a Facebook App
1. Go to [Facebook Developers](https://developers.facebook.com/)
2. Click "My Apps" → "Create App"
3. Choose "Business" type
4. Add your business and complete setup

### Step 2: Configure Webhooks
1. In your app dashboard, go to "Products" → "Webhooks"
2. Click "Add Subscription" → Select "Page"
3. Subscribe to the `leadgen` field
4. Enter Callback URL: `https://YOUR_DOMAIN/api/v1/facebook-leads/webhook`
5. Enter Verify Token: Use the value you'll set as `FACEBOOK_WEBHOOK_VERIFY_TOKEN`

### Step 3: Get Page Access Token
1. Go to "Tools" → "Graph API Explorer"
2. Select your app and page
3. Request permissions: `leads_retrieval`, `pages_manage_ads`, `pages_read_engagement`
4. Generate and copy the access token
5. **Important**: Convert to a long-lived token for production use

### Step 4: Get App Secret
1. In your app dashboard, go to "Settings" → "Basic"
2. Copy the "App Secret" value

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/facebook-leads/webhook` | Facebook verification (automatic) |
| POST | `/api/v1/facebook-leads/webhook` | Receives lead notifications |
| GET | `/api/v1/facebook-leads/config` | Check integration status (requires auth) |
| POST | `/api/v1/facebook-leads/test-lead` | Create test lead (VGK4U/EA users) |
| GET | `/api/v1/facebook-leads/leads` | View received Facebook leads (requires auth) |

## Field Mapping

Facebook form fields are automatically mapped to CRM fields:

| Facebook Field | CRM Field |
|----------------|-----------|
| `full_name` or `first_name + last_name` | `name` |
| `email` | `email` |
| `phone_number` | `phone` |
| `city` | `city` |
| `state` | `state` |
| `country` | `country` |
| `zip_code` | (included in notes) |
| `job_title` | (included in notes) |
| `company_name` | `company_name` |
| Other fields | Stored in `description` |

## Lead Processing

1. Facebook sends webhook notification when a lead is submitted
2. System verifies the request signature using `FACEBOOK_APP_SECRET`
3. System fetches full lead data from Facebook Graph API
4. Lead is created in CRM with:
   - Source: "Facebook Lead Ads"
   - Status: "new"
   - Priority: "high"
   - Auto-assigned to first active company

## Testing the Integration

### Using the Test Endpoint
Staff users with VGK4U or EA roles can create test leads:

```json
POST /api/v1/facebook-leads/test-lead
{
    "company_id": 1,
    "name": "Test Lead Name",
    "email": "test@example.com",
    "phone": "9876543210"
}
```

### Checking Configuration Status
```
GET /api/v1/facebook-leads/config
Authorization: Bearer <your_token>
```

Returns configuration status including whether all required secrets are set.

## Troubleshooting

### Leads Not Being Captured
1. Verify all 3 environment secrets are set correctly
2. Check webhook URL is accessible (must be HTTPS in production)
3. Verify page access token has correct permissions
4. Check CRM module has at least one active company

### Signature Verification Failed
1. Ensure `FACEBOOK_APP_SECRET` matches your app's secret
2. Check the webhook is receiving the raw request body

### Cannot Fetch Lead Data
1. Verify `FACEBOOK_PAGE_ACCESS_TOKEN` is valid and not expired
2. Confirm token has `leads_retrieval` permission

## Security Notes

- All webhook requests are verified using HMAC SHA256 signature
- Page access tokens should be long-lived and stored securely
- Webhook verify token should be a secure random string
- Never expose these secrets in client-side code
