from functools import wraps
from flask import request, current_app, jsonify
import jwt

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'missing authorization header'}), 401
        
        try:
            scheme, token = auth_header.split(' ')
            if scheme.lower() != 'bearer':
                return jsonify({'error': 'invalid authorization scheme'}), 401
            
            payload = jwt.decode(token, current_app.config['JWT_SECRET'], algorithms=[current_app.config.get('JWT_ALGORITHM', 'HS256')])
            user_id = payload.get('sub')
            if not user_id:
                return jsonify({'error': 'invalid token'}), 401
            
            # Attach user_id to request for the route handler
            request.user_id = user_id
            return f(*args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'token expired'}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({'error': 'invalid token'}), 401
        except Exception as e:
            return jsonify({'error': 'auth error'}), 401
    
    return decorated
