from flask import Blueprint, request, current_app, jsonify, make_response
from .. import db
from ..models import User, RefreshToken
import bcrypt as _bcrypt_lib
import jwt
from datetime import datetime, timedelta
import uuid
import hashlib
import traceback
import logging

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)


def create_access_token(user_id):
    secret = current_app.config['JWT_SECRET']
    alg = current_app.config.get('JWT_ALGORITHM', 'HS256')
    exp = datetime.utcnow() + timedelta(
        minutes=current_app.config.get('ACCESS_TOKEN_EXPIRE_MINUTES', 15)
    )
    payload = {'sub': user_id, 'exp': exp}
    return jwt.encode(payload, secret, algorithm=alg)


def create_refresh_token():
    return str(uuid.uuid4())


@auth_bp.route('/signup', methods=['POST'])
def signup():
    try:
        data = request.get_json() or {}
        email = data.get('email')
        password = data.get('password')
        display_name = data.get('display_name')

        if not email or not password:
            return jsonify({'error': 'email and password required'}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'email already exists'}), 409

        # Truncate password to 72 bytes (bcrypt limit). Work with bytes
        # to ensure we never hand >72 bytes to the backend.
        password_bytes = password.encode('utf-8')
        password_truncated_bytes = password_bytes[:72]
        # Use bcrypt.hashpw directly to avoid passlib backend detection issues
        salt = _bcrypt_lib.gensalt()
        pw_hash = _bcrypt_lib.hashpw(password_truncated_bytes, salt).decode('utf-8')

        user = User(
            email=email,
            password_hash=pw_hash,
            display_name=display_name or email.split('@')[0]
        )
        db.session.add(user)
        db.session.flush()
        
        # Auto-join public channels
        from ..models import Channel, ChannelMembership
        public_channels = Channel.query.filter_by(is_private=False).all()
        for channel in public_channels:
            membership = ChannelMembership(channel_id=channel.id, user_id=user.id, role='member')
            db.session.add(membership)
        
        db.session.commit()

        access = create_access_token(user.id)
        refresh = create_refresh_token()
        refresh_hash = hashlib.sha256(refresh.encode()).hexdigest()

        rt = RefreshToken(
            user_id=user.id,
            token_hash=refresh_hash,
            expires_at=datetime.utcnow() + timedelta(
                days=current_app.config.get('REFRESH_TOKEN_EXPIRE_DAYS', 30)
            )
        )
        db.session.add(rt)
        db.session.commit()

        resp = jsonify({'user': user.to_dict(), 'access_token': access})
        resp.set_cookie(
            'refresh_token', 
            refresh, 
            httponly=True, 
            samesite='Lax', 
            secure=False, 
            path='/'
        )

        return resp, 201

    except Exception as e:
        logger.error(f'Signup error: {str(e)}\n{traceback.format_exc()}')
        db.session.rollback()
        return jsonify({'error': 'server error: ' + str(e)}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json() or {}
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({'error': 'email and password required'}), 400

        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'error': 'invalid credentials'}), 401

        # Truncate password to 72 bytes (bcrypt limit). Work with bytes
        # to ensure we never hand >72 bytes to the backend.
        password_bytes = password.encode('utf-8')
        password_truncated_bytes = password_bytes[:72]
        try:
            stored = user.password_hash.encode('utf-8')
        except Exception:
            stored = user.password_hash
        if not _bcrypt_lib.checkpw(password_truncated_bytes, stored):
            return jsonify({'error': 'invalid credentials'}), 401

        access = create_access_token(user.id)
        refresh = create_refresh_token()
        refresh_hash = hashlib.sha256(refresh.encode()).hexdigest()

        rt = RefreshToken(
            user_id=user.id,
            token_hash=refresh_hash,
            expires_at=datetime.utcnow() + timedelta(
                days=current_app.config.get('REFRESH_TOKEN_EXPIRE_DAYS', 30)
            )
        )
        db.session.add(rt)
        db.session.commit()

        resp = jsonify({'user': user.to_dict(), 'access_token': access})
        resp.set_cookie(
            'refresh_token', 
            refresh, 
            httponly=True, 
            samesite='Lax', 
            secure=False, 
            path='/'
        )

        return resp, 200

    except Exception as e:
        logger.error(f'Login error: {str(e)}\n{traceback.format_exc()}')
        db.session.rollback()
        return jsonify({'error': 'server error: ' + str(e)}), 500


@auth_bp.route('/refresh', methods=['POST'])
def refresh():
    refresh_token = request.cookies.get('refresh_token')
    if not refresh_token:
        return jsonify({'error': 'no refresh token'}), 401

    refresh_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    rt = RefreshToken.query.filter_by(token_hash=refresh_hash).first()

    if not rt or (rt.expires_at and rt.expires_at < datetime.utcnow()):
        return jsonify({'error': 'invalid or expired refresh token'}), 401

    access = create_access_token(rt.user_id)
    return jsonify({'access_token': access}), 200


@auth_bp.route('/logout', methods=['POST'])
def logout():
    resp = make_response('', 204)
    resp.set_cookie('refresh_token', '', expires=0)
    return resp
