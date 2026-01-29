"""
BloxStake API Server
Handles MM2 item storage, withdrawals, deposits, and user management
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from functools import wraps
import asyncio
import os
from datetime import datetime, timedelta
from database import Database
from verification import RobloxVerification
from security import SecurityManager

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration
API_KEY = os.environ.get("API_KEY", "YOUR_API_KEY_HERE")
SECURITY_KEY = os.environ.get("SECURITY_KEY", "YOUR_SECURITY_KEY_HERE")

# Initialize components
db = None
verification = None
security = None

# In-memory storage for withdrawal sessions (use Redis in production)
withdrawal_sessions = {}

def require_api_key(f):
    """Decorator to require API key authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        provided_key = request.headers.get('X-API-Key') or request.json.get('key')
        if not provided_key or provided_key != API_KEY:
            return jsonify({"error": "Invalid or missing API key"}), 401
        return f(*args, **kwargs)
    return decorated_function

def verify_security_key(f):
    """Decorator to verify security key in request data"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        data = request.json or {}
        security_key = data.get('SecurityKey') or data.get('Data', {}).get('SecurityKey')
        if not security_key or security_key != SECURITY_KEY:
            return jsonify({"error": "Invalid security key"}), 403
        return f(*args, **kwargs)
    return decorated_function

@app.before_request
async def before_request():
    """Initialize database connection before each request"""
    global db, verification, security
    if db is None:
        db = Database()
        await db.connect()
        verification = RobloxVerification(db)
        security = SecurityManager(SECURITY_KEY)

@app.route('/', methods=['GET'])
def home():
    """Health check endpoint"""
    return jsonify({
        "service": "BloxStake API",
        "status": "online",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    })

@app.route('/api/mm2/MurderMystery2/Trading/Withdraw/GetSession', methods=['POST'])
@require_api_key
async def get_withdrawal_session():
    """Check if user has an active withdrawal session"""
    data = request.json.get('Data', {})
    user_id = data.get('UserId')
    
    if not user_id:
        return jsonify({"error": "UserId required"}), 400
    
    # Check if session exists
    session = withdrawal_sessions.get(user_id)
    
    if session:
        # Check if session hasn't expired (30 minutes)
        if datetime.fromisoformat(session['created_at']) + timedelta(minutes=30) > datetime.utcnow():
            return jsonify({
                "Exists": True,
                "Items": session['items'],
                "CreatedAt": session['created_at']
            })
        else:
            # Session expired, remove it
            del withdrawal_sessions[user_id]
    
    return jsonify({"Exists": False})

@app.route('/api/mm2/MurderMystery2/Trading/Withdraw/CreateSession', methods=['POST'])
@require_api_key
async def create_withdrawal_session():
    """Create a withdrawal session for a user"""
    data = request.json.get('Data', {})
    user_id = data.get('UserId')
    items = data.get('Items', {})
    
    if not user_id:
        return jsonify({"error": "UserId required"}), 400
    
    if not items:
        return jsonify({"error": "Items required"}), 400
    
    # Check if user has verified account
    # In real implementation, check database for verification
    
    # Create session
    withdrawal_sessions[user_id] = {
        "items": items,
        "created_at": datetime.utcnow().isoformat(),
        "status": "pending"
    }
    
    return jsonify({
        "success": True,
        "message": "Withdrawal session created",
        "session_id": user_id
    })

@app.route('/api/mm2/MurderMystery2/Trading/Withdraw/ConfirmSession', methods=['POST'])
@verify_security_key
async def confirm_withdrawal():
    """Confirm a withdrawal has been completed"""
    data = request.json.get('Data', {})
    user_id = data.get('UserId')
    
    if not user_id:
        return jsonify({"error": "UserId required"}), 400
    
    # Remove session
    if user_id in withdrawal_sessions:
        session = withdrawal_sessions[user_id]
        del withdrawal_sessions[user_id]
        
        # Log the withdrawal in database
        # In real implementation, update inventory here
        
        return jsonify({
            "success": True,
            "message": "Withdrawal confirmed",
            "items": session['items']
        })
    
    return jsonify({"error": "No active session found"}), 404

@app.route('/api/mm2/MurderMystery2/Trading/Deposit', methods=['POST'])
@verify_security_key
async def deposit_items():
    """Record deposited items"""
    data = request.json.get('Data', {})
    user_id = data.get('UserId')
    items = data.get('items', [])
    
    if not user_id:
        return jsonify({"error": "UserId required"}), 400
    
    if not items:
        return jsonify({"error": "Items required"}), 400
    
    # Get or create Roblox user ID
    roblox_user_id = await verification.get_user_id(user_id)
    
    if not roblox_user_id:
        return jsonify({"error": "Could not resolve Roblox user"}), 400
    
    # Add items to inventory
    for item in items:
        await db.add_item_to_inventory(
            roblox_user_id=roblox_user_id,
            item_name=item.get('name'),
            game_name=item.get('gameName'),
            quantity=item.get('quantity', 1),
            asset_id=item.get('assetId'),
            holder=item.get('holder')
        )
    
    # Create trade record
    await db.create_trade_record(roblox_user_id, "deposit", items)
    
    return jsonify({
        "success": True,
        "message": f"Deposited {len(items)} items",
        "userId": user_id
    })

@app.route('/api/mm2/MurderMystery2/Inventory/Get', methods=['POST'])
@require_api_key
async def get_inventory():
    """Get user's inventory"""
    data = request.json.get('Data', {})
    user_id = data.get('UserId')
    
    if not user_id:
        return jsonify({"error": "UserId required"}), 400
    
    # Resolve username to ID
    roblox_user_id = await verification.get_user_id(user_id)
    
    if not roblox_user_id:
        return jsonify({"error": "User not found"}), 404
    
    # Get inventory from database
    inventory = await db.get_inventory(roblox_user_id)
    
    return jsonify({
        "success": True,
        "items": inventory,
        "count": len(inventory)
    })

@app.route('/api/mm2/MurderMystery2/User/CheckVerified', methods=['POST'])
@require_api_key
async def check_verified():
    """Check if a Roblox user is verified on Discord"""
    data = request.json.get('Data', {})
    roblox_user_id = data.get('RobloxUserId')
    
    if not roblox_user_id:
        return jsonify({"error": "RobloxUserId required"}), 400
    
    # Check if any Discord user has verified this Roblox account
    # This is a simple check - in production you'd want more robust verification
    async with db.connection.execute(
        "SELECT COUNT(*) as count FROM verifications WHERE roblox_user_id = ? AND verified = 1",
        (roblox_user_id,)
    ) as cursor:
        row = await cursor.fetchone()
        is_verified = row['count'] > 0 if row else False
    
    return jsonify({
        "Verified": is_verified,
        "RobloxUserId": roblox_user_id
    })

@app.route('/api/mm2/MurderMystery2/Stats', methods=['GET'])
@require_api_key
async def get_stats():
    """Get system statistics"""
    # Count users
    async with db.connection.execute("SELECT COUNT(*) as count FROM users") as cursor:
        row = await cursor.fetchone()
        user_count = row['count'] if row else 0
    
    # Count verified users
    async with db.connection.execute("SELECT COUNT(*) as count FROM verifications WHERE verified = 1") as cursor:
        row = await cursor.fetchone()
        verified_count = row['count'] if row else 0
    
    # Count inventory items
    async with db.connection.execute("SELECT COUNT(*) as count FROM inventory") as cursor:
        row = await cursor.fetchone()
        item_count = row['count'] if row else 0
    
    return jsonify({
        "total_users": user_count,
        "verified_users": verified_count,
        "total_items": item_count,
        "active_sessions": len(withdrawal_sessions)
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
