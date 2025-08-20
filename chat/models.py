from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """Extended user model with premium status"""
    is_premium = models.BooleanField(default=False, help_text="Premium membership status")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'auth_user'


class Lobby(models.Model):
    """Chat lobby/room model"""
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_game', 'In Game'),
        ('closed', 'Closed'),
    ]
    
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_lobbies')
    is_public = models.BooleanField(default=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='open')
    max_participants = models.PositiveIntegerField(default=8)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Lobbies"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.owner.username})"

    @property
    def current_participants_count(self):
        return self.memberships.count()

    @property
    def is_full(self):
        return self.current_participants_count >= self.max_participants

    def can_join(self, user):
        """Check if user can join this lobby"""
        if self.status != 'open':
            return False, "Lobby is not open"
        if self.is_full:
            return False, "Lobby is full"
        if self.bans.filter(user=user).exists():
            return False, "You are banned from this lobby"
        if self.memberships.filter(user=user).exists():
            return False, "Already in lobby"
        return True, "Can join"


class LobbyMembership(models.Model):
    """User membership in a lobby"""
    ROLE_CHOICES = [
        ('member', 'Member'),
        ('moderator', 'Moderator'),
        ('owner', 'Owner'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lobby_memberships')
    lobby = models.ForeignKey(Lobby, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'lobby']
        ordering = ['joined_at']

    def __str__(self):
        return f"{self.user.username} in {self.lobby.name} ({self.role})"


class LobbyBan(models.Model):
    """Banned users from a lobby"""
    lobby = models.ForeignKey(Lobby, on_delete=models.CASCADE, related_name='bans')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lobby_bans')
    reason = models.TextField(blank=True, null=True)
    banned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='bans_issued')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['lobby', 'user']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} banned from {self.lobby.name}"


class Message(models.Model):
    """Chat messages in lobbies"""
    lobby = models.ForeignKey(Lobby, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.sender.username}: {self.content[:50]}"


class LobbyEvent(models.Model):
    """Audit log for lobby events"""
    EVENT_TYPES = [
        ('kick', 'User Kicked'),
        ('ban', 'User Banned'),
        ('unban', 'User Unbanned'),
        ('transfer', 'Ownership Transferred'),
        ('mod_add', 'Moderator Added'),
        ('mod_remove', 'Moderator Removed'),
        ('status_change', 'Status Changed'),
    ]
    
    lobby = models.ForeignKey(Lobby, on_delete=models.CASCADE, related_name='events')
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='lobby_actions')
    target = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='lobby_events_received')
    description = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.event_type} in {self.lobby.name} by {self.actor}"
