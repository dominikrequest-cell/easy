# BloxStake Deployment Guide

## Deploy to Render

### Option 1: Automatic Deployment (Recommended)

1. **Push to GitHub** (already done!)
   ```bash
   git push origin main
   ```

2. **Connect to Render**
   - Go to [render.com](https://render.com)
   - Sign up/login with GitHub
   - Click "New +"
   - Select "Blueprint"
   - Connect your `dominikrequest-cell/easy` repository
   - Render will auto-detect `render.yaml` and create both services!

3. **Set Environment Variables**
   - Go to the Discord bot service
   - Add `BOT_TOKEN` with your Discord bot token
   - API keys will be auto-generated

### Option 2: Manual Deployment

#### Deploy API (Web Service):

1. Go to Render Dashboard
2. Click "New +" → "Web Service"
3. Connect GitHub repo: `dominikrequest-cell/easy`
4. Settings:
   - **Name**: `bloxstake-api`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn api:app`
   - **Plan**: Free
5. Add environment variables:
   - `API_KEY`: (generate a secure random string)
   - `SECURITY_KEY`: (generate a secure random string)
   - `PORT`: 10000
6. Click "Create Web Service"

Your API will be live at: `https://bloxstake-api.onrender.com`

#### Deploy Discord Bot (Background Worker):

1. Go to Render Dashboard
2. Click "New +" → "Background Worker"
3. Connect GitHub repo: `dominikrequest-cell/easy`
4. Settings:
   - **Name**: `bloxstake-discord-bot`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python discord_bot.py`
   - **Plan**: Free
5. Add environment variables:
   - `BOT_TOKEN`: (your Discord bot token)
   - `API_KEY`: (same as API service)
   - `SECURITY_KEY`: (same as API service)
6. Click "Create Background Worker"

## After Deployment

### 1. Update API URLs

Once your API is deployed, update these files:

**discord_bot.py:**
```python
API_BASE = "https://bloxstake-api.onrender.com/api/mm2/"
```

**bloxstake.lua:**
```lua
local api = "https://bloxstake-api.onrender.com/api/mm2/"
```

### 2. Set API Keys

Copy the API keys from Render and update:
- Discord bot environment variables
- Lua script (for Roblox bot)

### 3. Test Your Setup

**Test API:**
```bash
curl https://bloxstake-api.onrender.com/
```

Should return:
```json
{
  "service": "BloxStake API",
  "status": "online",
  "version": "1.0.0"
}
```

**Test Discord Bot:**
In your Discord server, type:
```
!help_mm2
```

## Important Notes

### Free Tier Limitations:
- ⚠️ **Web services sleep after 15 minutes** of inactivity
- ⚠️ **Background workers run 24/7** but may restart occasionally
- ⚠️ **750 hours/month** free for all services combined

### Keep API Awake (Optional):
Use a service like [UptimeRobot](https://uptimerobot.com) to ping your API every 5 minutes:
```
https://bloxstake-api.onrender.com/
```

### Database Persistence:
- SQLite files are stored on disk
- ⚠️ Render may reset disk on redeploy
- **For production**: Upgrade to Render PostgreSQL or external DB

## Monitoring

### Check Logs:
- Go to Render Dashboard
- Select your service
- Click "Logs" tab

### Check Status:
```bash
curl https://bloxstake-api.onrender.com/api/mm2/MurderMystery2/Stats \
  -H "X-API-Key: YOUR_API_KEY"
```

## Troubleshooting

**API not responding:**
- Check Render logs for errors
- Verify environment variables are set
- Ensure `PORT` is set to 10000

**Discord bot offline:**
- Verify `BOT_TOKEN` is correct
- Check Render logs for connection errors
- Ensure bot has proper Discord permissions

**Database errors:**
- Database initializes on first request
- Check if SQLite file has write permissions
- Consider upgrading to PostgreSQL for production

## Custom Domain (Optional)

1. Go to your API service settings
2. Click "Settings" → "Custom Domain"
3. Add: `api.bloxstake.com`
4. Update DNS records as instructed
5. Wait for SSL certificate (automatic)

## Security Recommendations

1. **Never commit real API keys** to GitHub
2. **Use environment variables** for all secrets
3. **Rotate API keys** regularly
4. **Enable Render's built-in DDoS protection**
5. **Monitor API usage** for suspicious activity

## Next Steps

1. ✅ Deploy both services to Render
2. ✅ Update API URLs in code
3. ✅ Set environment variables
4. ✅ Test all functionality
5. ✅ Monitor logs for 24 hours
6. 🚀 Launch BloxStake!
