# Railway Environment Variables for Gmail Webhooks

## 🚀 Required Environment Variables

Add these to your Railway project environment variables:

### **Gmail Webhook Configuration**
```bash
GMAIL_WEBHOOK_URL=https://hr-automation-backend-production-1d70.up.railway.app/api/gmail/webhook
GOOGLE_CLOUD_PROJECT_ID=jarvis-voice-assistant-467210
GMAIL_WEBHOOK_SECRET=your-super-secret-webhook-key-here
```

## 🔧 How to Set in Railway:

1. Go to [Railway Dashboard](https://railway.app/)
2. Select your `hr-automation-backend-production` project
3. Go to **Variables** tab
4. Add each variable above

## 📝 Notes:

- **GMAIL_WEBHOOK_URL**: Your production webhook endpoint
- **GOOGLE_CLOUD_PROJECT_ID**: Your existing Google Cloud project ID
- **GMAIL_WEBHOOK_SECRET**: Generate a random 16+ character secret for webhook verification

## 🔑 Generate Webhook Secret:

```bash
# Generate a random secret (run this locally)
openssl rand -hex 32
# or
python -c "import secrets; print(secrets.token_hex(32))"
```

## ✅ Verification:

After setting these variables, restart your Railway deployment and check the logs for:
```
✅ All required webhook environment variables are configured
```
