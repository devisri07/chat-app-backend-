
from flask import Blueprint, jsonify

health_bp = Blueprint('health', __name__)

# This new route handles the base URL (/)
# This fixes the "Not Found" error when you visit the main deployment URL.
@health_bp.route('/', methods=['GET'])
def welcome():
    """Returns a status message on the root URL."""
    return jsonify({
        "status": "online",
        "service": "Chat Application Backend",
        "message": "Backend is running successfully. Official health check is at /healthz"
    }), 200

# Your existing health check route
@health_bp.route('/healthz', methods=['GET'])
def health():
    """Returns the official status OK for health monitoring."""
    return jsonify({'status': 'ok'}), 200