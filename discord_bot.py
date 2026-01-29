import discord
from discord.ext import commands
import aiohttp
import json
from typing import Optional
from database import Database
from verification import RobloxVerification
from security import SecurityManager

# Configuration
API_BASE = "https://api.bloxstake.com/api/mm2/"  # Update with your BloxStake API endpoint
API_KEY = "YOUR_API_KEY_HERE"  # Replace with your actual API key
SECURITY_KEY = "YOUR_SECURITY_KEY_HERE"  # Replace with your actual security key
BOT_TOKEN = "YOUR_DISCORD_BOT_TOKEN_HERE"

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

class BloxStakeAPI:
    """Wrapper for BloxStake API interactions"""
    
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.headers = {"Content-Type": "application/json"}
    
    async def create_withdrawal_session(self, user_id: str, items: dict) -> dict:
        """Create a withdrawal session for a user"""
        url = f"{API_BASE}MurderMystery2/Trading/Withdraw/CreateSession"
        payload = {
            "Data": {
                "UserId": user_id,
                "Items": items
            },
            "SecurityKey": SECURITY_KEY,
            "key": API_KEY
        }
        
        async with self.session.post(url, json=payload, headers=self.headers) as resp:
            return await resp.json()
    
    async def get_withdrawal_session(self, user_id: str) -> dict:
        """Check if user has an active withdrawal session"""
        url = f"{API_BASE}MurderMystery2/Trading/Withdraw/GetSession"
        payload = {
            "Data": {
                "UserId": user_id
            }
        }
        
        async with self.session.post(url, json=payload, headers=self.headers) as resp:
            return await resp.json()
    
    async def confirm_withdrawal(self, user_id: str) -> dict:
        """Confirm a withdrawal was completed"""
        url = f"{API_BASE}MurderMystery2/Trading/Withdraw/ConfirmSession"
        payload = {
            "Data": {
                "UserId": user_id
            },
            "SecurityKey": SECURITY_KEY
        }
        
        async with self.session.post(url, json=payload, headers=self.headers) as resp:
            return await resp.json()
    
    async def get_inventory(self, user_id: str) -> dict:
        """Get user's stored inventory"""
        url = f"{API_BASE}MurderMystery2/Inventory/Get"
        payload = {
            "Data": {
                "UserId": user_id
            },
            "key": API_KEY
        }
        
        async with self.session.post(url, json=payload, headers=self.headers) as resp:
            return await resp.json()
    
    async def deposit_items(self, user_id: str, items: list) -> dict:
        """Record deposited items"""
        url = f"{API_BASE}MurderMystery2/Trading/Deposit"
        payload = {
            "Data": {
                "UserId": user_id,
                "items": items
            },
            "SecurityKey": SECURITY_KEY,
            "key": API_KEY
        }
        
        async with self.session.post(url, json=payload, headers=self.headers) as resp:
            return await resp.json()

# Global session
session: Optional[aiohttp.ClientSession] = None
api: Optional[BloxStakeAPI] = None
db: Optional[Database] = None
verification: Optional[RobloxVerification] = None
security: Optional[SecurityManager] = None

@bot.event
async def on_ready():
    global session, api, db, verification, security
    session = aiohttp.ClientSession()
    api = BloxStakeAPI(session)
    
    # Initialize database and verification
    db = Database()
    await db.connect()
    verification = RobloxVerification(db)
    security = SecurityManager(SECURITY_KEY)
    
    print(f'{bot.user} is now online!')
    print(f'Connected to {len(bot.guilds)} servers')
    print('Verification system enabled!')

@bot.event
async def on_close():
    if session:
        await session.close()
    if verification:
        await verification.close()
    if db:
        await db.close()

@bot.command(name="verify")
async def verify_account(ctx, roblox_username: str):
    """Start verification process to link your Roblox account
    
    Usage: !verify <roblox_username>
    Example: !verify PlayerName123
    """
    discord_id = ctx.author.id
    
    # Validate username format
    is_valid, error = security.is_valid_username(roblox_username)
    if not is_valid:
        await ctx.send(f"❌ Invalid username: {error}")
        return
    
    # Get Roblox user ID
    roblox_user_id = await verification.get_user_id(roblox_username)
    if not roblox_user_id:
        await ctx.send(f"❌ Could not find Roblox user '{roblox_username}'. Please check the spelling.")
        return
    
    # Generate verification code
    challenge = security.create_verification_challenge(discord_id, roblox_user_id)
    code = challenge["code"]
    
    # Store in database
    await db.create_verification(discord_id, roblox_user_id, code)
    
    # Get user thumbnail
    thumbnail = await verification.get_user_thumbnail(roblox_user_id)
    
    embed = discord.Embed(
        title="🔐 Verify Your Roblox Account",
        description=f"To link **{roblox_username}** to your Discord account:",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="Step 1",
        value="Copy the verification code below",
        inline=False
    )
    embed.add_field(
        name="Step 2",
        value="Go to [roblox.com](https://www.roblox.com) and edit your profile description/bio",
        inline=False
    )
    embed.add_field(
        name="Step 3",
        value="Paste the code anywhere in your bio and save",
        inline=False
    )
    embed.add_field(
        name="Step 4",
        value="Come back and type `!checkverify`",
        inline=False
    )
    embed.add_field(
        name="📋 Verification Code",
        value=f"```{code}```",
        inline=False
    )
    
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    
    embed.set_footer(text="This code expires in 24 hours")
    
    await ctx.send(embed=embed)

@bot.command(name="checkverify")
async def check_verification(ctx):
    """Check if your verification code has been added to your Roblox bio
    
    Usage: !checkverify
    """
    discord_id = ctx.author.id
    
    # Get verification entry
    verification_data = await db.get_verification(discord_id)
    if not verification_data:
        await ctx.send("❌ No verification in progress. Use `!verify <username>` first.")
        return
    
    if verification_data["verified"]:
        await ctx.send("✅ You're already verified!")
        return
    
    roblox_user_id = verification_data["roblox_user_id"]
    code = verification_data["verification_code"]
    
    # Check if code is in bio
    await ctx.send("🔍 Checking your Roblox bio...")
    
    if await verification.verify_code_in_description(roblox_user_id, code):
        # Mark as verified
        await db.mark_verified(discord_id)
        
        username = await verification.get_username(roblox_user_id)
        thumbnail = await verification.get_user_thumbnail(roblox_user_id)
        
        embed = discord.Embed(
            title="✅ Verification Successful!",
            description=f"Your Discord account is now linked to **{username}**",
            color=discord.Color.green()
        )
        embed.add_field(
            name="What's Next?",
            value="You can now use `!inventory`, `!withdraw`, and other commands!\n\n*You can remove the code from your bio now.*",
            inline=False
        )
        
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ Verification code not found in your Roblox bio. Make sure you:\n" +
                      "1. Copied the entire code\n" +
                      "2. Pasted it in your profile description\n" +
                      "3. Saved your profile changes\n\n" +
                      "Try again in a few minutes (it may take time to update).")

@bot.command(name="myaccount")
async def my_account(ctx):
    """View your linked Roblox account
    
    Usage: !myaccount
    """
    discord_id = ctx.author.id
    roblox_user_id = await db.get_roblox_id_by_discord(discord_id)
    
    if not roblox_user_id:
        await ctx.send("❌ You haven't verified your account yet. Use `!verify <username>` to get started.")
        return
    
    username = await verification.get_username(roblox_user_id)
    thumbnail = await verification.get_user_thumbnail(roblox_user_id)
    
    embed = discord.Embed(
        title="🎮 Your Linked Account",
        color=discord.Color.blue()
    )
    embed.add_field(name="Roblox Username", value=username, inline=True)
    embed.add_field(name="Roblox ID", value=str(roblox_user_id), inline=True)
    embed.add_field(name="Status", value="✅ Verified", inline=True)
    
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    
    await ctx.send(embed=embed)

@bot.command(name="withdraw")
async def withdraw(ctx, item_name: str, quantity: int = 1):
    """Request a withdrawal from your storage
    
    Usage: !withdraw <item_name> [quantity]
    Example: !withdraw "Chroma Lightbringer" 1
    """
    discord_id = ctx.author.id
    
    # Check if user is verified
    roblox_user_id = await db.get_roblox_id_by_discord(discord_id)
    if not roblox_user_id:
        await ctx.send("❌ You must verify your Roblox account first! Use `!verify <username>`")
        return
    
    user_id = str(roblox_user_id)
    
    # Check if user already has an active session
    # Note: The existing API uses Roblox username as UserId, not Roblox user ID
    roblox_username = await verification.get_username(roblox_user_id)
    existing = await api.get_withdrawal_session(roblox_username)
    if existing.get("Exists"):
        await ctx.send("❌ You already have an active withdrawal session! Complete it first or cancel it.")
        return
    
    # Create withdrawal session using Roblox username as identifier
    items = {item_name: quantity}
    result = await api.create_withdrawal_session(roblox_username, items)
    
    if result.get("success"):
        embed = discord.Embed(
            title="✅ Withdrawal Request Created",
            description=f"Your withdrawal request has been created!",
            color=discord.Color.green()
        )
        embed.add_field(name="Item", value=item_name, inline=True)
        embed.add_field(name="Quantity", value=quantity, inline=True)
        embed.add_f"Join the MM2 bot server with your Roblox account **{roblox_username}**
            name="Next Steps",
            value="Join the MM2 bot server and send a trade request to complete your withdrawal.",
            inline=False
        )
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"❌ Failed to create withdrawal request: {result.get('message', 'Unknown error')}")

@bot.command(name="inventory")
async def inventory(ctx):
    """View your stored items
    
    Usage: !inventory
    """
    discord_id = ctx.author.id
    
    # Check if user is verified
    roblox_user_id = await db.get_roblox_id_by_discord(discord_id)
    if not roblox_user_id:
        await ctx.send("❌ You must verify your Roblox account first! Use `!verify <username>`")
    # The API uses Roblox username, not ID
    roblox_username = await verification.get_username(roblox_user_id)
    
    result = await api.get_inventory(roblox_username
    
    result = await api.get_inventory(user_id)
    
    if result.get("success"):
        items = result.get("items", [])
        
        if not items:
            await ctx.send("📦 Your storage is empty!")
            return
        
        embed = discord.Embed(
            title="📦 Your MM2 Storage",
            description=f"Total items: {len(items)}",
            color=discord.Color.blue()
        )
        
        # Group items and show quantities
        item_counts = {}
        for item in items:
            item_name = item.get("name", "Unknown")
            item_counts[item_name] = item_counts.get(item_name, 0) + 1
        
        for item_name, count in sorted(item_counts.items()):
            embed.add_field(name=item_name, value=f"x{count}", inline=True)
        
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"❌ Failed to fetch inventory: {result.get('message', 'Unknown error')}")

@bot.command(name="deposit")
async def deposit_info(ctx):
    """Get instructions for depositing items
    
    Usage: !deposit
    """
    embed = discord.Embed(
        title="💰 How to Deposit Items",
        description="Follow these steps to deposit items into your storage:",
        color=discord.Color.gold()
    )
    embed.add_field(
        name="Step 1",
        value="Join the MM2 bot server (ask for invite link)",
        inline=False
    )
    embed.add_field(
        name="Step 2",
        value="Send a trade request to the bot",
        inline=False
    )
    embed.add_field(
        name="Step 3",
        value="Add the items you want to deposit",
        inline=False
    )
    embed.add_field(
        name="Step 4",
        value="Accept the trade - your items will be automatically credited!",
        inline=False
    )
    embed.add_field(
        name="⚠️ Important",
        value="**Do NOT deposit pets!** They are not supported and will not be credited.",
        inline=False
    )
    embed.set_footer(text="BloxStake - Secure Item Storage for Murder Mystery 2")
    await ctx.send(embed=embed)

@bot.command(name="status")
async def status(ctx):
    """Check if you have any pending withdrawals
    
    Usage: !status
    """
    discord_id = ctx.author.id
    
    # Check if user is verified
    roblox_user_id = await db.get_roblox_id_by_discord(discord_id)
    if not roblox_user_id:
        await ctx.send("❌ You must verify your Roblox account first! Use `!verify <username>`")
        return
    
    # The API uses Roblox username
    roblox_username = await verification.get_username(roblox_user_id)
    
    result = await api.get_withdrawal_session(roblox_username)
    
    if result.get("Exists"):
        items = result.get("Items", {})
        
        embed = discord.Embed(
            title="⏳ Pending Withdrawal",
            description="You have an active withdrawal request:",
            color=discord.Color.orange()
        )
        
        for item_name, quantity in items.items():
            embed.add_field(name=item_name, value=f"x{quantity}", inline=True)
        
        embed.add_field(
            name="Action Required",
            value="Join the bot server and send a trade request to complete this withdrawal.",
            inline=False
        )
        
        await ctx.send(embed=embed)
    else:
        await ctx.send("✅ No pending withdrawals. Your account is clear!")

@bot.command(name="cancel")
async def cancel_withdrawal(ctx):
    """Cancel your pending withdrawal request
    
    Usage: !cancel
    """
    discord_id = ctx.author.id
    
    # Check if user is verified
    roblox_user_id = await db.get_roblox_id_by_discord(discord_id)
    if not roblox_user_id:
        await ctx.send("❌ You must verify your Roblox account first! Use `!verify <username>`")
        return
    
    # The API uses Roblox username
    roblox_username = await verification.get_username(roblox_user_id)
    
    # Attempt to confirm/cancel by completing the session
    result = await api.confirm_withdrawal(roblox_username)
    
    if result.get("success"):
        await ctx.send("✅ Your withdrawal request has been cancelled.")
    else:
        await ctx.send("❌ No active withdrawal to cancel, or cancellation failed.")

@bot.command(name="help_mm2")
async def help_mm2(ctx):
    """Show all available commands
    
    Usage: !help_mm2
    """verify <username>", "Link your Roblox account"),
        ("!checkverify", "Complete verification process"),
        ("!myaccount", "View linked Roblox account"),
        ("!
    embed = discord.Embed(
        title="🎮 MM2Stash Bot Commands",
        description="Manage your Murder Mystery 2 item storage",
        color=discord.Color.purple()
    )
    
    commands_info = [
        ("!inventory", "View all items in your storage"),
        ("!withdraw <item> [qty]", "Request to withdraw items"),
        ("!deposit", "Get instructions for depositing items"),
tructions
    embed = discord.Embed(
        title="🔗 Account Linking",
        description=f"Attempting to link to Roblox account: **{roblox_username}**",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="Note",
        value="This feature requires database integration. Your Discord ID will be used as your identifier for now.",
        inline=False
    )
    await ctx.send(embed=embed)

# Error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Unknown command. Use `!help_mm2` to see available commands.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument. Use `!help_mm2` for command usage.")
    else:
        await ctx.send(f"❌ An error occurred: {str(error)}")
        print(f"Error: {error}")

if __name__ == "__main__":
    print("Starting MM2Stash Discord Bot...")
    print("Make sure to set your Discord bot token!")
    bot.run(BOT_TOKEN)
