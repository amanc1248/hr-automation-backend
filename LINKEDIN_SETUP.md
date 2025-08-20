# LinkedIn API Integration Setup Guide

## Overview
This guide will help you set up real LinkedIn API integration for automated job posting and application collection.

## Prerequisites
- LinkedIn Developer Account
- Company LinkedIn Page (for posting jobs)
- Python 3.11+ environment

## Step 1: LinkedIn Developer Setup

### 1.1 Create LinkedIn App
1. Visit [LinkedIn Developers](https://www.linkedin.com/developers/)
2. Click **"Create App"**
3. Fill in app details:
   - **App Name**: "HR Automation System"
   - **LinkedIn Page**: Your company's LinkedIn page
   - **App Logo**: Upload company logo
   - **App Description**: "AI-powered hiring automation system"

### 1.2 Configure OAuth 2.0 Settings
1. Go to **"Auth"** tab in your app
2. Add **Redirect URLs**:
   - `http://localhost:8001/auth/linkedin/callback` (development)
   - `https://yourdomain.com/auth/linkedin/callback` (production)
3. Note your **Client ID** and **Client Secret**

### 1.3 Request API Permissions
Go to **"Products"** tab and add:
- **Marketing Developer Platform**
- **Sign In with LinkedIn**
- **Share on LinkedIn**
- **Marketing APIs**

Required permissions:
- `r_liteprofile` - Read basic profile
- `r_organization_social` - Read company posts
- `w_organization_social` - Write company posts
- `r_ads_reporting` - Read analytics (optional)

## Step 2: Environment Configuration

### 2.1 Update .env File
```bash
# LinkedIn Configuration
LINKEDIN_CLIENT_ID=your_client_id_here
LINKEDIN_CLIENT_SECRET=your_client_secret_here
LINKEDIN_ACCESS_TOKEN=your_access_token_here

# Optional: LinkedIn Company ID
LINKEDIN_COMPANY_ID=your_company_id_here
```

### 2.2 Generate Access Token
1. Use LinkedIn's OAuth 2.0 flow
2. Or use LinkedIn's Access Token Generator (for testing)
3. Store token securely (consider using environment variables)

## Step 3: LinkedIn API Endpoints

### 3.1 Job Posting Endpoint
```
POST https://api.linkedin.com/v2/ugcPosts
```

### 3.2 Company Page Endpoint
```
GET https://api.linkedin.com/v2/organizations/{company_id}
```

### 3.3 Job Applications Endpoint
```
GET https://api.linkedin.com/v2/jobs/{job_id}/applications
```

## Step 4: Testing the Integration

### 4.1 Test Job Posting
```bash
curl -X POST "http://localhost:8001/api/jobs/" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Senior Full Stack Engineer",
    "description": "Join our amazing team...",
    "posted_platforms": ["linkedin"]
  }'
```

### 4.2 Monitor Workflow
```bash
curl "http://localhost:8001/api/plan-runs/"
```

## Step 5: Troubleshooting

### Common Issues:
1. **Invalid Access Token**: Regenerate token in LinkedIn Developer Console
2. **Permission Denied**: Ensure all required permissions are granted
3. **Rate Limiting**: LinkedIn has API rate limits (100 requests/day for free tier)
4. **Company Page Access**: Ensure your app has access to the company page

### Debug Mode:
Enable debug logging in your .env:
```bash
LOG_LEVEL=DEBUG
LINKEDIN_DEBUG=true
```

## Step 6: Production Considerations

### Security:
- Store credentials securely (use environment variables)
- Implement token refresh mechanism
- Monitor API usage and rate limits

### Monitoring:
- Log all LinkedIn API calls
- Track job posting success rates
- Monitor application collection metrics

## Support Resources

- [LinkedIn API Documentation](https://developer.linkedin.com/docs)
- [LinkedIn Marketing API](https://developer.linkedin.com/docs/marketing-api)
- [OAuth 2.0 Flow](https://developer.linkedin.com/docs/oauth2)
- [Rate Limits](https://developer.linkedin.com/docs/guide/v2/rate-limits)

## Next Steps

After completing this setup:
1. Test job posting with real LinkedIn API
2. Implement application collection
3. Add analytics and monitoring
4. Scale to multiple job boards
