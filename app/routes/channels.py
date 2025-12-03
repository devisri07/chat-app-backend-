from flask import Blueprint, request, jsonify, current_app
from .. import db
from ..models import Channel, ChannelMembership, User
from ..auth_decorator import require_auth
import logging

logger = logging.getLogger(__name__)
channels_bp = Blueprint('channels', __name__)


@channels_bp.route('/', methods=['GET'], strict_slashes=False)
@require_auth
def list_channels():
    """List all channels the user is a member of, or public channels."""
    try:
        user_id = request.user_id
        # Get channels user is a member of
        memberships = ChannelMembership.query.filter_by(user_id=user_id).all()
        channel_ids = [m.channel_id for m in memberships]
        channels = Channel.query.filter(Channel.id.in_(channel_ids)).all() if channel_ids else []
        # Also get public channels
        public_channels = Channel.query.filter_by(is_private=False).all()
        all_channels = list({c.id: c for c in channels + public_channels}.values())
        return jsonify({'channels': [c.to_dict() for c in all_channels]}), 200
    except Exception as e:
        logger.error(f'List channels error: {str(e)}')
        return jsonify({'error': 'server error'}), 500


@channels_bp.route('/', methods=['POST'], strict_slashes=False)
@require_auth
def create_channel():
    """Create a new channel."""
    try:
        user_id = request.user_id
        data = request.get_json() or {}
        name = data.get('name')
        is_private = data.get('is_private', False)
        
        if not name or not name.strip():
            return jsonify({'error': 'name required'}), 400
        
        channel = Channel(name=name.strip(), is_private=bool(is_private), owner_id=user_id)
        db.session.add(channel)
        db.session.flush()
        
        # Add creator as member
        membership = ChannelMembership(channel_id=channel.id, user_id=user_id, role='owner')
        db.session.add(membership)
        db.session.commit()
        
        return jsonify({'channel': channel.to_dict()}), 201
    except Exception as e:
        logger.error(f'Create channel error: {str(e)}')
        db.session.rollback()
        return jsonify({'error': 'server error'}), 500


@channels_bp.route('/<channel_id>/join', methods=['POST'], strict_slashes=False)
@require_auth
def join_channel(channel_id):
    """Join a channel."""
    try:
        user_id = request.user_id
        channel = Channel.query.get(channel_id)
        
        if not channel:
            return jsonify({'error': 'channel not found'}), 404
        
        if channel.is_private:
            return jsonify({'error': 'cannot join private channel'}), 403
        
        # Check if already a member
        existing = ChannelMembership.query.filter_by(channel_id=channel_id, user_id=user_id).first()
        if existing:
            return jsonify({'ok': True}), 200
        
        membership = ChannelMembership(channel_id=channel_id, user_id=user_id, role='member')
        db.session.add(membership)
        db.session.commit()
        
        return jsonify({'ok': True}), 200
    except Exception as e:
        logger.error(f'Join channel error: {str(e)}')
        db.session.rollback()
        return jsonify({'error': 'server error'}), 500


@channels_bp.route('/<channel_id>/members', methods=['GET'], strict_slashes=False)
@require_auth
def get_channel_members(channel_id):
    """Get members of a channel."""
    try:
        user_id = request.user_id
        
        # Verify user is a member
        membership = ChannelMembership.query.filter_by(channel_id=channel_id, user_id=user_id).first()
        if not membership:
            return jsonify({'error': 'not a member'}), 403
        
        members = db.session.query(User, ChannelMembership).join(
            ChannelMembership, User.id == ChannelMembership.user_id
        ).filter(ChannelMembership.channel_id == channel_id).all()
        
        return jsonify({
            'members': [
                {
                    'id': u.id,
                    'email': u.email,
                    'display_name': u.display_name,
                    'role': m.role
                }
                for u, m in members
            ]
        }), 200
    except Exception as e:
        logger.error(f'Get members error: {str(e)}')
        return jsonify({'error': 'server error'}), 500


@channels_bp.route('/<channel_id>', methods=['GET'], strict_slashes=False)
@require_auth
def get_channel(channel_id):
    """Get channel details."""
    try:
        user_id = request.user_id
        channel = Channel.query.get(channel_id)
        
        if not channel:
            return jsonify({'error': 'not found'}), 404
        
        # Verify user is a member (unless public)
        if channel.is_private:
            membership = ChannelMembership.query.filter_by(channel_id=channel_id, user_id=user_id).first()
            if not membership:
                return jsonify({'error': 'not a member'}), 403
        
        member_count = ChannelMembership.query.filter_by(channel_id=channel_id).count()
        return jsonify({
            'channel': channel.to_dict(),
            'member_count': member_count
        }), 200
    except Exception as e:
        logger.error(f'Get channel error: {str(e)}')
        return jsonify({'error': 'server error'}), 500


@channels_bp.route('/<channel_id>/leave', methods=['POST'], strict_slashes=False)
@require_auth
def leave_channel(channel_id):
    """Leave a channel."""
    try:
        user_id = request.user_id
        membership = ChannelMembership.query.filter_by(channel_id=channel_id, user_id=user_id).first()
        
        
        if membership:
            db.session.delete(membership)
            db.session.commit()
        
        return '', 204
    except Exception as e:
        logger.error(f'Leave channel error: {str(e)}')
        db.session.rollback()
        return jsonify({'error': 'server error'}), 500


@channels_bp.route('/<channel_id>', methods=['DELETE'], strict_slashes=False)
@require_auth
def delete_channel(channel_id):
    """Delete a channel (owner only)."""
    try:
        user_id = request.user_id
        channel = Channel.query.get(channel_id)
        
        if not channel:
            return jsonify({'error': 'channel not found'}), 404
        
        if channel.owner_id != user_id:
            return jsonify({'error': 'only owner can delete'}), 403
        
        # Delete all memberships
        ChannelMembership.query.filter_by(channel_id=channel_id).delete()
        # Delete all messages
        from ..models import Message
        Message.query.filter_by(channel_id=channel_id).delete()
        # Delete channel
        db.session.delete(channel)
        db.session.commit()
        
        return '', 204
    except Exception as e:
        logger.error(f'Delete channel error: {str(e)}')
        db.session.rollback()
        return jsonify({'error': 'server error'}), 500
