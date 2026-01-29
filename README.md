# BloxStake Discord Bot with Verification System

A Discord bot that interfaces with the BloxStake API, allowing users to manage their Murder Mystery 2 item storage directly from Discord. **Now includes Roblox account verification** to ensure secure, verified trades.

## Features

- 🔐 **Account Verification** - Link Discord to Roblox via bio verification
- 📦 **View Inventory** - Check all stored items
- 💸 **Request Withdrawals** - Create withdrawal requests for items
- 💰 **Deposit Instructions** - Get step-by-step deposit guidance
- ⏳ **Check Status** - View pending withdrawal requests
- ❌ **Cancel Requests** - Cancel active withdrawals
- 🛡️ **Secure** - Payload signing, verification codes, anti-replay protection

## Architecture

```
Discord User → Verification → Discord Bot → MM2Stash API
                    ↓              ↓              ↓
              Roblox Bio       Database       Roblox Bot
                Check                          (Verified Trades Only)
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Create Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Go to "Bot" section and create a bot
4. Copy the bot token
5. Enable "Message Content Intent" under Privileged Gateway Intents

### 3. Configure Bot

Edit `discord_bot.py` and replace `BOT_TOKEN` on line 11 with your Discord bot token

### 4. Invite Bot to Server

Use this URL (replace `YOUR_CLIENT_ID` with your application's client ID):
```
https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=2048&scope=bot
```

### 5. Run the Bot

```bash
python discord_bot.py
```

## User Flow

### First-Time Setup (Verification)

1. User types `!verify PlayerName123` in Discord
2. Bot generates a unique verification code
3. User adds code to their Roblox profile bio
4. User types `!checkverify` in Discord
5. Bot checks Roblox API for code in bio
6. ✅ Account is now linked and verified!

### Depositing Items

1. User types `!deposit` for instructions
2. User joins Roblox bot server
3. User sends trade to bot (bot checks verification)
4. User adds items to trade
5. Bot automatically credits items to user's account

### Withdrawing Items

1. User types `!withdraw "Chroma Lightbringer" 1`
2. Bot creates withdrawal session
3. User joins Roblox bot server
4. Bot checks verification, then adds items to trade
5. Trade completes automatically

## Commands

| Command | Description | Usage |
|---------|-------------|-------|
| `!verify` | Link Roblox account | `!verify PlayerName123` |
| `!checkverify` | Complete verification | `!checkverify` |
| `!myaccount` | View linked account | `!myaccount` |
| `!inventory` | View stored items | `!inventory` |
| `!withdraw` | Request withdrawal | `!withdraw "Chroma Lightbringer" 1` |
| `!deposit` | Get deposit instructions | `!deposit` |
| `!status` | Check pending requests | `!status` |
| `!cancel` | Cancel withdrawal | `!cancel` |
| `!help_mm2` | Show all commands | `!help_mm2` |

## Database Schema

The bot uses SQLite with the following tables:

- **users** - Cached Roblox user data (ID, username, bio, thumbnail)
- **verifications** - Discord↔Roblox links with verification codes
- **inventory** - User item storage
- **trade_history** - Trade logs and audit trail

## Security Features

### Verification System
- **Bio Verification**: Users must prove Roblox account ownership
- **Unique Codes**: 16-word verification codes from word list
- **One-Time Link**: Each Discord can only link one Roblox account
- **Cached Data**: Reduces API calls, improves performance

### Trade Security
- **HMAC Signing**: All payloads signed with SHA256
- **Timestamp Validation**: Prevents replay attacks (5min window)
- **Verified-Only Trades**: Lua bot rejects unverified users
- **Secure Comparison**: Timing-attack-resistant verification

## Files

- [discord_bot.py](discord_bot.py) - Main Discord bot with commands
- [database.py](database.py) - SQLite database layer
- [verification.py](verification.py) - Roblox API integration & verification
- [security.py](security.py) - HMAC signing & verification codes
- [bloxstake.lua](bloxstake.lua) - Roblox bot script
- [requirements.txt](requirements.txt) - Python dependencies

## Roblox Bot Integration

The Roblox bot works with the existing BloxStake API. Verification enforcement happens at the Discord bot level:

- Only verified Discord users can create withdrawal requests via `!withdraw`
- The Roblox bot checks the existing API for pending withdrawal sessions
- Users must use their verified Roblox account to complete trades
- Deposits are automatically credited to the Roblox username that traded

## API Endpoints Used

The bot uses these existing BloxStake API endpoints:

- `POST /MurderMystery2/Trading/Withdraw/GetSession` - Get withdrawal session (existing)
- `POST /MurderMystery2/Trading/Withdraw/ConfirmSession` - Confirm withdrawal (existing)
- `POST /MurderMystery2/Trading/Deposit` - Record deposits (existing)
- `POST /MurderMystery2/Inventory/Get` - Get user inventory (existing)

**Note**: Verification is handled entirely within the Discord bot's database. The external API doesn't need any modifications.

## Future Enhancements

- [ ] Re-verification after inactivity
- [ ] Trade history viewing in Discord
- [ ] Item value estimates from community data
- [ ] Automated notifications when trades complete
- [ ] Admin panel for bot management
- [ ] Multi-game support (PS99, etc.)
- [ ] Slash commands support
- [ ] Rate limiting per user
- [ ] 2FA for high-value withdrawals

## Troubleshooting

**"You must verify your Roblox account first!"**
- Use `!verify <username>` to start the verification process

**"Verification code not found in your Roblox bio"**
- Make sure you copied the ENTIRE code
- Wait 1-2 minutes for Roblox to update your profile
- Check that you saved your profile changes

**"Could not find Roblox user"**
- Double-check the spelling of your username
- Usernames are case-insensitive but must be exact

## Support

For issues or questions, contact the BloxStake support team.
