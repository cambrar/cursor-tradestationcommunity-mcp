# Authentication Guide

TradeStation Community uses Auth0 OAuth with AWS WAF CAPTCHA protection. This requires a hybrid authentication approach.

## The Challenge

- **AWS WAF CAPTCHA**: Protects against bots (cannot be automated)
- **Auth0 OAuth**: JavaScript-based authentication flow
- **Session Cookies**: Required for forum access

## Solution: Cookie-Based Authentication

### One-Time Setup (On Your Mac)

1. **Install dependencies locally:**
   ```bash
   cd /Users/rcambra/personal/Cursor/cursor-tradestationcommunity-mcp
   python3 -m venv venv
   source venv/bin/activate
   pip install playwright python-dotenv
   playwright install chromium
   ```

2. **Run the cookie saver script:**
   ```bash
   python save-cookies.py
   ```

3. **In the browser window that opens:**
   - Solve the AWS WAF CAPTCHA (click the puzzle)
   - Enter your TradeStation username/password
   - Click "Log In"
   - Wait for the forum page to fully load
   - Return to the terminal and press Enter

4. **The script will save cookies to:** `.session_cookies.json`

5. **Copy cookies to EC2:**
   ```bash
   scp .session_cookies.json mcp-server@35.87.167.11:/data/tradestation-community-mcp/
   ```

6. **Update and restart the MCP server on EC2:**
   ```bash
   ssh mcp-server@35.87.167.11
   cd /data/tradestation-community-mcp
   git pull
   sudo ./update.sh
   sudo systemctl restart tradestation-community-mcp  # if using systemd
   ```

### How It Works

1. **Initial authentication** happens manually on your Mac (with GUI browser)
2. **Session cookies are extracted** and saved to a file
3. **EC2 MCP server loads cookies** on startup
4. **Cookies are used for all forum requests** (no more login needed)
5. **Cookies last for days/weeks** before expiring

### When Cookies Expire

You'll know cookies have expired when searches return no results or you get login errors.

**To refresh cookies:**
```bash
# On your Mac
cd /Users/rcambra/personal/Cursor/cursor-tradestationcommunity-mcp
source venv/bin/activate
python save-cookies.py

# Copy to EC2
scp .session_cookies.json mcp-server@35.87.167.11:/data/tradestation-community-mcp/

# Restart MCP server
ssh mcp-server@35.87.167.11 "sudo systemctl restart tradestation-community-mcp"
```

## Alternative: Run Cookie Saver on EC2 with X11 Forwarding

If you want to run the cookie saver directly on EC2:

```bash
# Enable X11 forwarding
ssh -X mcp-server@35.87.167.11

# Run the script
cd /data/tradestation-community-mcp
sudo -u mcp-server DISPLAY=:0 ./venv/bin/python save-cookies.py
```

**Note:** This requires X11 server running on your Mac (like XQuartz).

## Security Notes

- **Cookie file contains authentication tokens** - keep it secure
- **File permissions are set to 600** (readable only by owner)
- **Cookies are stored locally** on EC2, not in git
- **Never commit** `.session_cookies.json` to version control

## Troubleshooting

### "Doesn't look like you're logged in"
- Make sure you see the actual forum page (with threads listed)
- Wait a few extra seconds after login before pressing Enter
- Check that the browser URL contains "Discussions" or "Forum.aspx"

### Browser doesn't open
- Make sure you're running on your Mac, not EC2
- Check that Playwright is installed: `playwright install chromium`
- Try running with: `PLAYWRIGHT_BROWSERS_PATH=0 python save-cookies.py`

### Cookies expire quickly
- This is normal - TradeStation may have short session timeouts
- Re-run the cookie saver script when needed
- Consider running it weekly as a maintenance task
