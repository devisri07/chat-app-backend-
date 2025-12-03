from flask import current_app, request
from flask_socketio import join_room, leave_room, emit, disconnect
from . import socketio, db
from .models import Message, Channel, ChannelMembership, User
import jwt
import logging

logger = logging.getLogger(__name__)

# Store connected user IDs per socket
socket_users = {}
# Track online users per channel: {channel_id: {user_id: {display_name, sid}}}
channel_users = {}


@socketio.on('connect')
def handle_connect(auth):
    """Authenticate socket connection via JWT token."""
    token = None
    if auth and isinstance(auth, dict):
        token = auth.get('token')
    
    if not token:
        logger.warning('Socket connect without token')
        return False
    
    try:
        payload = jwt.decode(token, current_app.config['JWT_SECRET'], 
                           algorithms=[current_app.config.get('JWT_ALGORITHM', 'HS256')])
        user_id = payload.get('sub')
        if not user_id:
            logger.warning('Invalid token: no sub')
            return False
        
        # Store user_id for this socket
        socket_users[request.sid] = user_id
        user = User.query.get(user_id)
        emit('connected', {
            'user_id': user_id,
            'display_name': user.display_name if user else 'Unknown'
        })
        logger.info(f'Socket connected: {request.sid} -> user {user_id}')
        return True
    except jwt.ExpiredSignatureError:
        logger.warning('Socket auth: token expired')
        return False
    except jwt.InvalidTokenError as e:
        logger.warning(f'Socket auth: invalid token - {str(e)}')
        return False
    except Exception as e:
        logger.error(f'Socket auth error: {str(e)}')
        return False


@socketio.on('disconnect')
def handle_disconnect():
    """Clean up on disconnect."""
    if request.sid in socket_users:
        user_id = socket_users[request.sid]
        # Remove user from all channel tracking
        for channel_id in list(channel_users.keys()):
            if user_id in channel_users[channel_id]:
                del channel_users[channel_id][user_id]
                # Notify others in the channel
                room = f'channel:{channel_id}'
                user = User.query.get(user_id)
                emit('presence_update', {
                    'user_id': user_id,
                    'display_name': user.display_name if user else 'Unknown',
                    'action': 'left'
                }, room=room)
        logger.info(f'Socket disconnected: {request.sid} -> user {user_id}')
        del socket_users[request.sid]


@socketio.on('join_channel')
def handle_join_channel(data):
    """Join a channel room and broadcast presence."""
    try:
        if request.sid not in socket_users:
            return {'error': 'not authenticated'}
        
        user_id = socket_users[request.sid]
        channel_id = data.get('channel_id')
        
        if not channel_id:
            return {'error': 'channel_id required'}
        
        # Verify membership
        membership = ChannelMembership.query.filter_by(
            channel_id=channel_id, user_id=user_id
        ).first()
        if not membership:
            return {'error': 'not a member'}
        
        # Join room
        room = f'channel:{channel_id}'
        join_room(room)
        
        # Get current user info
        user = User.query.get(user_id)
        user_display_name = user.display_name if user else 'Unknown'
        
        # Initialize channel tracking if needed
        if channel_id not in channel_users:
            channel_users[channel_id] = {}
        
        # Add this user to the channel's online users
        channel_users[channel_id][user_id] = {
            'display_name': user_display_name,
            'sid': request.sid
        }
        
        # Send current online users list to joining client
        online_users_dict = {}
        for uid, user_info in channel_users[channel_id].items():
            online_users_dict[uid] = {
                'id': uid,
                'display_name': user_info['display_name']
            }
        emit('online_users_list', {'users': online_users_dict})
        
        # Broadcast presence update to room
        emit('presence_update', {
            'user_id': user_id,
            'display_name': user_display_name,
            'action': 'joined'
        }, room=room)
        
        logger.info(f'User {user_id} joined channel {channel_id}, online: {list(channel_users[channel_id].keys())}')
        return {'ok': True}
    except Exception as e:
        logger.error(f'Join channel error: {str(e)}')
        return {'error': 'server error'}


@socketio.on('leave_channel')
def handle_leave_channel(data):
    """Leave a channel room."""
    try:
        if request.sid not in socket_users:
            return {'error': 'not authenticated'}
        
        user_id = socket_users[request.sid]
        channel_id = data.get('channel_id')
        
        if not channel_id:
            return {'error': 'channel_id required'}
        
        room = f'channel:{channel_id}'
        leave_room(room)
        
        # Remove user from channel tracking
        if channel_id in channel_users and user_id in channel_users[channel_id]:
            del channel_users[channel_id][user_id]
        
        user = User.query.get(user_id)
        emit('presence_update', {
            'user_id': user_id,
            'display_name': user.display_name if user else 'Unknown',
            'action': 'left'
        }, room=room)
        
        logger.info(f'User {user_id} left channel {channel_id}')
        return {'ok': True}
    except Exception as e:
        logger.error(f'Leave channel error: {str(e)}')
        return {'error': 'server error'}


@socketio.on('send_message')
def handle_send_message(data):
    """Send a message to a channel."""
    try:
        if request.sid not in socket_users:
            return {'error': 'not authenticated'}
        
        user_id = socket_users[request.sid]
        channel_id = data.get('channel_id')
        content = data.get('content', '').strip()
        temp_id = data.get('temp_id')
        
        if not channel_id or not content:
            return {'error': 'channel_id and content required'}
        
        if len(content) > 4000:
            return {'error': 'message too long'}
        
        # Verify membership
        membership = ChannelMembership.query.filter_by(
            channel_id=channel_id, user_id=user_id
        ).first()
        if not membership:
            return {'error': 'not a member'}
        
        # Create and persist message
        msg = Message(channel_id=channel_id, user_id=user_id, content=content)
        db.session.add(msg)
        db.session.commit()
        
        # Broadcast to room
        user = User.query.get(user_id)
        message_data = msg.to_dict(user=user)
        message_data['temp_id'] = temp_id
        
        room = f'channel:{channel_id}'
        emit('message', message_data, room=room)
        
        logger.info(f'User {user_id} sent message to channel {channel_id}')
        return {'ok': True, 'id': msg.id}
    except Exception as e:
        logger.error(f'Send message error: {str(e)}')
        db.session.rollback()
        return {'error': 'server error'}


@socketio.on('typing')
def handle_typing(data):
    """Broadcast typing indicator."""
    try:
        if request.sid not in socket_users:
            return
        
        user_id = socket_users[request.sid]
        channel_id = data.get('channel_id')
        is_typing = data.get('is_typing', False)
        
        if not channel_id:
            return
        
        room = f'channel:{channel_id}'
        emit('typing', {
            'user_id': user_id,
            'is_typing': is_typing
        }, room=room, skip_sid=request.sid)
    except Exception as e:
        logger.error(f'Typing error: {str(e)}')
