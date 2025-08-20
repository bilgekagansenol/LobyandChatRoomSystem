from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from urllib.parse import parse_qs
import jwt

User = get_user_model()


class JWTAuthMiddleware(BaseMiddleware):
    """JWT Authentication middleware for WebSocket connections"""
    
    def __init__(self, inner):
        super().__init__(inner)
    
    async def __call__(self, scope, receive, send):
        # Get token from query parameters
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]
        
        if token:
            try:
                # Validate token
                UntypedToken(token)
                # Decode token to get user
                decoded_data = jwt.decode(
                    token, 
                    options={"verify_signature": False}
                )
                user_id = decoded_data.get('user_id')
                if user_id:
                    scope['user'] = await self.get_user(user_id)
                else:
                    scope['user'] = AnonymousUser()
            except (InvalidToken, TokenError, KeyError):
                scope['user'] = AnonymousUser()
        else:
            scope['user'] = AnonymousUser()
        
        return await super().__call__(scope, receive, send)
    
    @database_sync_to_async
    def get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return AnonymousUser()


def JWTAuthMiddlewareStack(inner):
    """WebSocket middleware stack with JWT authentication"""
    return JWTAuthMiddleware(inner)