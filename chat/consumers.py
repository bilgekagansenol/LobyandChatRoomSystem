import json
import asyncio
from typing import Dict, Any
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.cache import cache
from django.utils import timezone
from datetime import datetime, timedelta
from .models import User, Lobby, LobbyMembership, LobbyBan, Message


class LobbyConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for lobby chat"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lobby_id = None
        self.lobby_group_name = None
        self.user = None
        self.lobby = None
        
    async def connect(self):
        """Handle WebSocket connection"""
        self.lobby_id = self.scope['url_route']['kwargs']['lobby_id']
        self.lobby_group_name = f'lobby_{self.lobby_id}'
        self.user = self.scope['user']
        
        # Check if user is authenticated
        if not self.user.is_authenticated:
            await self.close(code=4001)
            return
        
        # Get lobby and check permissions
        self.lobby = await self.get_lobby()
        if not self.lobby:
            await self.close(code=4004)
            return
        
        # Check if user can join (not banned, lobby is open, etc.)
        can_join, reason = await self.can_user_join()
        if not can_join:
            await self.send_error(reason)
            await self.close(code=4003)
            return
        
        # Join lobby group
        await self.channel_layer.group_add(
            self.lobby_group_name,
            self.channel_name
        )
        
        # Accept connection
        await self.accept()
        
        # Add user to online presence
        await self.add_user_presence()
        
        # Notify others that user joined
        await self.channel_layer.group_send(
            self.lobby_group_name,
            {
                'type': 'presence_join',
                'user_id': self.user.id,
                'username': self.user.username,
                'is_premium': self.user.is_premium,
            }
        )
        
        # Send current online users to new user
        online_users = await self.get_online_users()
        await self.send(text_data=json.dumps({
            'type': 'presence_list',
            'users': online_users
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if hasattr(self, 'lobby_group_name') and self.lobby_group_name:
            # Remove user from online presence
            await self.remove_user_presence()
            
            # Notify others that user left
            if self.user and self.user.is_authenticated:
                await self.channel_layer.group_send(
                    self.lobby_group_name,
                    {
                        'type': 'presence_leave',
                        'user_id': self.user.id,
                        'username': self.user.username,
                    }
                )
            
            # Leave lobby group
            await self.channel_layer.group_discard(
                self.lobby_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """Handle received WebSocket message"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'chat_message':
                await self.handle_chat_message(data)
            elif message_type == 'typing_start':
                await self.handle_typing_start()
            elif message_type == 'typing_stop':
                await self.handle_typing_stop()
            else:
                await self.send_error('Unknown message type')
                
        except json.JSONDecodeError:
            await self.send_error('Invalid JSON')
        except Exception as e:
            await self.send_error(f'Error processing message: {str(e)}')
    
    async def handle_chat_message(self, data):
        """Handle chat message"""
        content = data.get('message', '').strip()
        
        if not content:
            await self.send_error('Message cannot be empty')
            return
        
        if len(content) > 2000:
            await self.send_error('Message too long (max 2000 characters)')
            return
        
        # Check rate limit
        if not await self.check_rate_limit():
            await self.send_error('Rate limit exceeded. Please slow down.')
            return
        
        # Check if user is still a member
        is_member = await self.is_user_member()
        if not is_member:
            await self.send_error('You are not a member of this lobby')
            await self.close(code=4003)
            return
        
        # Save message to database
        message = await self.save_message(content)
        if not message:
            await self.send_error('Failed to save message')
            return
        
        # Broadcast message to lobby group
        await self.channel_layer.group_send(
            self.lobby_group_name,
            {
                'type': 'chat_message',
                'message': {
                    'id': message.id,
                    'content': message.content,
                    'sender': {
                        'id': self.user.id,
                        'username': self.user.username,
                        'is_premium': self.user.is_premium,
                    },
                    'created_at': message.created_at.isoformat(),
                }
            }
        )
    
    async def handle_typing_start(self):
        """Handle typing start event"""
        await self.channel_layer.group_send(
            self.lobby_group_name,
            {
                'type': 'typing_start',
                'user_id': self.user.id,
                'username': self.user.username,
            }
        )
    
    async def handle_typing_stop(self):
        """Handle typing stop event"""
        await self.channel_layer.group_send(
            self.lobby_group_name,
            {
                'type': 'typing_stop',
                'user_id': self.user.id,
                'username': self.user.username,
            }
        )
    
    async def chat_message(self, event):
        """Send chat message to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message']
        }))
    
    async def presence_join(self, event):
        """Send presence join event to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'presence_join',
            'user_id': event['user_id'],
            'username': event['username'],
            'is_premium': event['is_premium'],
        }))
    
    async def presence_leave(self, event):
        """Send presence leave event to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'presence_leave',
            'user_id': event['user_id'],
            'username': event['username'],
        }))
    
    async def typing_start(self, event):
        """Send typing start event to WebSocket"""
        # Don't send typing events back to the sender
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'typing_start',
                'user_id': event['user_id'],
                'username': event['username'],
            }))
    
    async def typing_stop(self, event):
        """Send typing stop event to WebSocket"""
        # Don't send typing events back to the sender
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'typing_stop',
                'user_id': event['user_id'],
                'username': event['username'],
            }))
    
    async def moderation_kick(self, event):
        """Handle user kicked event"""
        if event['target_id'] == self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'moderation_kick',
                'reason': event.get('reason', ''),
                'message': 'You have been kicked from the lobby'
            }))
            await self.close(code=4003)
        else:
            await self.send(text_data=json.dumps({
                'type': 'moderation_kick',
                'target_id': event['target_id'],
                'target_username': event.get('target_username', ''),
                'reason': event.get('reason', ''),
            }))
    
    async def moderation_ban(self, event):
        """Handle user banned event"""
        if event['target_id'] == self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'moderation_ban',
                'reason': event.get('reason', ''),
                'message': 'You have been banned from the lobby'
            }))
            await self.close(code=4003)
        else:
            await self.send(text_data=json.dumps({
                'type': 'moderation_ban',
                'target_id': event['target_id'],
                'target_username': event.get('target_username', ''),
                'reason': event.get('reason', ''),
            }))
    
    async def system_status(self, event):
        """Handle lobby status change event"""
        await self.send(text_data=json.dumps({
            'type': 'system_status',
            'status': event['status'],
            'message': event.get('message', ''),
        }))
    
    async def send_error(self, message: str):
        """Send error message to client"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))
    
    # Database operations
    
    @database_sync_to_async
    def get_lobby(self):
        """Get lobby object"""
        try:
            return Lobby.objects.get(id=self.lobby_id)
        except Lobby.DoesNotExist:
            return None
    
    @database_sync_to_async
    def can_user_join(self):
        """Check if user can join lobby"""
        if not self.lobby:
            return False, "Lobby not found"
        
        return self.lobby.can_join(self.user)
    
    @database_sync_to_async
    def is_user_member(self):
        """Check if user is a member of the lobby"""
        return LobbyMembership.objects.filter(
            user=self.user,
            lobby=self.lobby
        ).exists()
    
    @database_sync_to_async
    def save_message(self, content: str):
        """Save message to database"""
        try:
            message = Message.objects.create(
                lobby=self.lobby,
                sender=self.user,
                content=content
            )
            return message
        except Exception:
            return None
    
    # Rate limiting
    
    async def check_rate_limit(self):
        """Check if user has exceeded rate limit"""
        cache_key = f'rate_limit:user:{self.user.id}:lobby:{self.lobby_id}'
        current_time = timezone.now()
        
        # Get current message timestamps
        messages = cache.get(cache_key, [])
        
        # Remove old messages (older than 2 seconds)
        cutoff_time = current_time - timedelta(seconds=2)
        messages = [msg_time for msg_time in messages if msg_time > cutoff_time]
        
        # Check if limit exceeded (3 messages per 2 seconds)
        if len(messages) >= 3:
            return False
        
        # Add current message timestamp
        messages.append(current_time)
        cache.set(cache_key, messages, timeout=10)
        
        return True
    
    # Presence management
    
    async def add_user_presence(self):
        """Add user to online presence set"""
        cache_key = f'lobby_presence:{self.lobby_id}'
        current_users = cache.get(cache_key, set())
        current_users.add(self.user.id)
        cache.set(cache_key, current_users, timeout=300)  # 5 minutes
    
    async def remove_user_presence(self):
        """Remove user from online presence set"""
        cache_key = f'lobby_presence:{self.lobby_id}'
        current_users = cache.get(cache_key, set())
        current_users.discard(self.user.id)
        if current_users:
            cache.set(cache_key, current_users, timeout=300)
        else:
            cache.delete(cache_key)
    
    @database_sync_to_async
    def get_online_users(self):
        """Get list of online users"""
        cache_key = f'lobby_presence:{self.lobby_id}'
        user_ids = cache.get(cache_key, set())
        
        if not user_ids:
            return []
        
        users = User.objects.filter(id__in=user_ids).values(
            'id', 'username', 'is_premium'
        )
        return list(users)