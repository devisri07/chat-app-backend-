from flask import Blueprint, request, jsonify
from ..models import Message, Channel, ChannelMembership
from .. import db
from ..auth_decorator import require_auth
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
messages_bp = Blueprint('messages', __name__)


@messages_bp.route('/<channel_id>/messages', methods=['GET'], strict_slashes=False)
@require_auth
def get_messages(channel_id):
    """Get message history for a channel (cursor-based pagination)."""
    try:
        user_id = request.user_id
        
        # Verify user is a member of the channel
        membership = ChannelMembership.query.filter_by(channel_id=channel_id, user_id=user_id).first()
        if not membership:
            return jsonify({'error': 'not a member of this channel'}), 403
        
        # Cursor-based pagination: before=ISO timestamp or message_id
        before = request.args.get('before')
        limit = int(request.args.get('limit', 50))
        limit = min(limit, 100)  # Cap at 100 to prevent abuse
        
        query = Message.query.filter_by(channel_id=channel_id, is_deleted=False).order_by(Message.created_at.desc())
        
        if before:
            try:
                before_dt = datetime.fromisoformat(before)
                query = query.filter(Message.created_at < before_dt)
            except Exception:
                pass
        
        messages = query.limit(limit + 1).all()
        has_more = len(messages) > limit
        messages = messages[:limit]
        
        # Reverse to show chronological order
        messages = list(reversed(messages))
        
        # Calculate next cursor
        next_cursor = None
        if has_more and messages:
            next_cursor = messages[0].created_at.isoformat()
        
        # Import User model for eager loading
        from ..models import User
        messages_data = []
        for m in messages:
            user = User.query.get(m.user_id) if m.user_id else None
            messages_data.append(m.to_dict(user=user))
        
        return jsonify({
            'messages': messages_data,
            'next_cursor': next_cursor,
            'has_more': has_more
        }), 200
    except Exception as e:
        logger.error(f'Get messages error: {str(e)}')
        return jsonify({'error': 'server error'}), 500


@messages_bp.route('/<channel_id>/messages', methods=['POST'], strict_slashes=False)
@require_auth
def create_message(channel_id):
    """Create a message in a channel."""
    try:
        user_id = request.user_id
        
        # Verify user is a member
        membership = ChannelMembership.query.filter_by(channel_id=channel_id, user_id=user_id).first()
        if not membership:
            return jsonify({'error': 'not a member of this channel'}), 403
        
        data = request.get_json() or {}
        content = data.get('content', '').strip()
        
        if not content or len(content) > 4000:
            return jsonify({'error': 'content required and must be < 4000 chars'}), 400
        
        msg = Message(channel_id=channel_id, user_id=user_id, content=content)
        db.session.add(msg)
        db.session.commit()
        
        return jsonify({'message': msg.to_dict()}), 201
    except Exception as e:
        logger.error(f'Create message error: {str(e)}')
        db.session.rollback()
        return jsonify({'error': 'server error'}), 500
