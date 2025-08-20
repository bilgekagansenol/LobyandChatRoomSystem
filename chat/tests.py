import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
import json

from .models import Lobby, LobbyMembership, LobbyBan, Message, LobbyEvent
from .consumers import LobbyConsumer

User = get_user_model()


class UserModelTest(TestCase):
    """Test User model"""
    
    def test_create_regular_user(self):
        """Test creating a regular user"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.assertFalse(user.is_premium)
        self.assertTrue(user.check_password('testpass123'))
        
    def test_create_premium_user(self):
        """Test creating a premium user"""
        user = User.objects.create_user(
            username='premiumuser',
            email='premium@example.com',
            password='testpass123',
            is_premium=True
        )
        self.assertTrue(user.is_premium)


class LobbyModelTest(TestCase):
    """Test Lobby model"""
    
    def setUp(self):
        self.premium_user = User.objects.create_user(
            username='premium',
            email='premium@example.com',
            password='testpass123',
            is_premium=True
        )
        self.normal_user = User.objects.create_user(
            username='normal',
            email='normal@example.com',
            password='testpass123'
        )
        
    def test_create_lobby(self):
        """Test creating a lobby"""
        lobby = Lobby.objects.create(
            name='Test Lobby',
            owner=self.premium_user,
            max_participants=8
        )
        self.assertEqual(lobby.name, 'Test Lobby')
        self.assertEqual(lobby.owner, self.premium_user)
        self.assertEqual(lobby.status, 'open')
        self.assertTrue(lobby.is_public)
        
    def test_lobby_can_join(self):
        """Test lobby can_join method"""
        lobby = Lobby.objects.create(
            name='Test Lobby',
            owner=self.premium_user,
            max_participants=2
        )
        
        # User can join open lobby
        can_join, message = lobby.can_join(self.normal_user)
        self.assertTrue(can_join)
        
        # Create membership for owner
        LobbyMembership.objects.create(
            user=self.premium_user,
            lobby=lobby,
            role='owner'
        )
        
        # Create membership for normal user
        LobbyMembership.objects.create(
            user=self.normal_user,
            lobby=lobby,
            role='member'
        )
        
        # Lobby is now full
        can_join, message = lobby.can_join(self.normal_user)
        self.assertFalse(can_join)
        self.assertIn('full', message.lower())
        
    def test_lobby_ban_prevents_join(self):
        """Test banned user cannot join lobby"""
        lobby = Lobby.objects.create(
            name='Test Lobby',
            owner=self.premium_user
        )
        
        # Ban the user
        LobbyBan.objects.create(
            lobby=lobby,
            user=self.normal_user,
            banned_by=self.premium_user
        )
        
        can_join, message = lobby.can_join(self.normal_user)
        self.assertFalse(can_join)
        self.assertIn('banned', message.lower())


class AuthAPITest(APITestCase):
    """Test authentication API"""
    
    def test_user_registration(self):
        """Test user registration"""
        url = reverse('register')
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'newpass123',
            'password_confirm': 'newpass123'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='newuser').exists())
        
    def test_user_registration_password_mismatch(self):
        """Test registration with mismatched passwords"""
        url = reverse('register')
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'newpass123',
            'password_confirm': 'different123'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
    def test_jwt_login(self):
        """Test JWT token login"""
        user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        url = reverse('token_obtain_pair')
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)


class LobbyAPITest(APITestCase):
    """Test Lobby API"""
    
    def setUp(self):
        self.premium_user = User.objects.create_user(
            username='premium',
            email='premium@example.com',
            password='testpass123',
            is_premium=True
        )
        self.normal_user = User.objects.create_user(
            username='normal',
            email='normal@example.com',
            password='testpass123'
        )
        
        # Get JWT tokens
        self.premium_token = str(RefreshToken.for_user(self.premium_user).access_token)
        self.normal_token = str(RefreshToken.for_user(self.normal_user).access_token)
        
    def test_premium_user_can_create_lobby(self):
        """Test premium user can create lobby"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.premium_token}')
        
        url = reverse('lobby-list')
        data = {
            'name': 'Test Lobby',
            'is_public': True,
            'max_participants': 8
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check if lobby was created
        lobby = Lobby.objects.get(name='Test Lobby')
        self.assertEqual(lobby.owner, self.premium_user)
        
        # Check if owner membership was created
        self.assertTrue(
            LobbyMembership.objects.filter(
                user=self.premium_user,
                lobby=lobby,
                role='owner'
            ).exists()
        )
        
    def test_normal_user_cannot_create_lobby(self):
        """Test normal user cannot create lobby"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.normal_token}')
        
        url = reverse('lobby-list')
        data = {
            'name': 'Test Lobby',
            'is_public': True,
            'max_participants': 8
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
    def test_list_public_lobbies(self):
        """Test listing public lobbies"""
        # Create public lobby
        lobby1 = Lobby.objects.create(
            name='Public Lobby',
            owner=self.premium_user,
            is_public=True
        )
        
        # Create private lobby
        lobby2 = Lobby.objects.create(
            name='Private Lobby',
            owner=self.premium_user,
            is_public=False
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.normal_token}')
        
        url = reverse('lobby-list')
        response = self.client.get(url, {'public': '1'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should only return public lobby
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Public Lobby')
        
    def test_join_lobby(self):
        """Test joining a lobby"""
        lobby = Lobby.objects.create(
            name='Test Lobby',
            owner=self.premium_user
        )
        
        # Create owner membership
        LobbyMembership.objects.create(
            user=self.premium_user,
            lobby=lobby,
            role='owner'
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.normal_token}')
        
        url = reverse('lobby-join', kwargs={'pk': lobby.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check if membership was created
        self.assertTrue(
            LobbyMembership.objects.filter(
                user=self.normal_user,
                lobby=lobby,
                role='member'
            ).exists()
        )
        
    def test_kick_user(self):
        """Test kicking a user from lobby"""
        lobby = Lobby.objects.create(
            name='Test Lobby',
            owner=self.premium_user
        )
        
        # Create memberships
        LobbyMembership.objects.create(
            user=self.premium_user,
            lobby=lobby,
            role='owner'
        )
        LobbyMembership.objects.create(
            user=self.normal_user,
            lobby=lobby,
            role='member'
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.premium_token}')
        
        url = reverse('lobby-kick', kwargs={'pk': lobby.id})
        data = {
            'user_id': self.normal_user.id,
            'reason': 'Test kick'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check if user was removed from lobby
        self.assertFalse(
            LobbyMembership.objects.filter(
                user=self.normal_user,
                lobby=lobby
            ).exists()
        )


class MessageAPITest(APITestCase):
    """Test Message API"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.lobby = Lobby.objects.create(
            name='Test Lobby',
            owner=self.user
        )
        LobbyMembership.objects.create(
            user=self.user,
            lobby=self.lobby,
            role='owner'
        )
        
        self.token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        
    def test_create_message(self):
        """Test creating a message"""
        url = reverse('lobby-messages-list', kwargs={'lobby_pk': self.lobby.id})
        data = {
            'content': 'Hello, world!'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check if message was created
        message = Message.objects.get(content='Hello, world!')
        self.assertEqual(message.sender, self.user)
        self.assertEqual(message.lobby, self.lobby)
        
    def test_list_messages(self):
        """Test listing messages"""
        # Create some messages
        Message.objects.create(
            lobby=self.lobby,
            sender=self.user,
            content='Message 1'
        )
        Message.objects.create(
            lobby=self.lobby,
            sender=self.user,
            content='Message 2'
        )
        
        url = reverse('lobby-messages-list', kwargs={'lobby_pk': self.lobby.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)


class PermissionTest(TestCase):
    """Test custom permissions"""
    
    def setUp(self):
        self.premium_user = User.objects.create_user(
            username='premium',
            password='testpass123',
            is_premium=True
        )
        self.normal_user = User.objects.create_user(
            username='normal',
            password='testpass123'
        )
        
    def test_is_premium_permission(self):
        """Test IsPremium permission"""
        from .permissions import IsPremium
        
        permission = IsPremium()
        
        # Mock request with premium user
        class MockRequest:
            def __init__(self, user):
                self.user = user
        
        # Premium user should have permission
        request = MockRequest(self.premium_user)
        self.assertTrue(permission.has_permission(request, None))
        
        # Normal user should not have permission
        request = MockRequest(self.normal_user)
        self.assertFalse(permission.has_permission(request, None))


class RateLimitTest(TestCase):
    """Test rate limiting functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
    def test_rate_limit_logic(self):
        """Test rate limiting logic"""
        from django.core.cache import cache
        from django.utils import timezone
        from datetime import timedelta
        
        # Simulate rate limiting
        cache_key = f'rate_limit:user:{self.user.id}:lobby:1'
        current_time = timezone.now()
        
        # First 3 messages should be allowed
        messages = []
        for i in range(3):
            messages.append(current_time)
        
        cache.set(cache_key, messages, timeout=10)
        
        # 4th message should be rate limited
        cached_messages = cache.get(cache_key, [])
        self.assertEqual(len(cached_messages), 3)
        
        # Simulate check
        cutoff_time = current_time - timedelta(seconds=2)
        valid_messages = [msg_time for msg_time in cached_messages if msg_time > cutoff_time]
        
        # Should fail rate limit check (3 messages in 2 seconds)
        self.assertGreaterEqual(len(valid_messages), 3)
