from rest_framework import permissions
from .models import LobbyMembership, LobbyBan


class IsPremium(permissions.BasePermission):
    """Permission to check if user has premium status"""
    
    def has_permission(self, request, view):
        return (
            request.user 
            and request.user.is_authenticated 
            and request.user.is_premium
        )


class IsOwnerOrModerator(permissions.BasePermission):
    """Permission to check if user is lobby owner or moderator"""
    
    def has_permission(self, request, view):
        print(f"DEBUG has_permission: User {request.user.username} calling action {view.action}")
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        print(f"DEBUG has_object_permission: User {request.user.username} on lobby {obj.id}")
        if not request.user.is_authenticated:
            return False
        
        # Check if user is owner
        if obj.owner == request.user:
            print(f"DEBUG: User {request.user.username} is owner")
            return True
        
        # Check if user is moderator
        try:
            membership = LobbyMembership.objects.get(
                lobby=obj, 
                user=request.user
            )
            is_moderator = membership.role in ['moderator', 'owner']
            print(f"DEBUG: User {request.user.username} role: {membership.role}, is_moderator: {is_moderator}")
            return is_moderator
        except LobbyMembership.DoesNotExist:
            print(f"DEBUG: User {request.user.username} not found in lobby {obj.id}")
            return False


class IsLobbyOwner(permissions.BasePermission):
    """Permission to check if user is lobby owner"""
    
    def has_object_permission(self, request, view, obj):
        return (
            request.user 
            and request.user.is_authenticated 
            and obj.owner == request.user
        )


class CanJoinLobby(permissions.BasePermission):
    """Permission to check if user can join lobby"""
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        can_join, message = obj.can_join(request.user)
        if not can_join:
            self.message = message
        return can_join


class IsNotBanned(permissions.BasePermission):
    """Permission to check if user is not banned from lobby"""
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        is_banned = LobbyBan.objects.filter(
            lobby=obj, 
            user=request.user
        ).exists()
        
        if is_banned:
            self.message = "You are banned from this lobby"
        return not is_banned


class IsLobbyMember(permissions.BasePermission):
    """Permission to check if user is a member of the lobby"""
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        is_member = LobbyMembership.objects.filter(
            lobby=obj,
            user=request.user
        ).exists()
        
        if not is_member:
            self.message = "You must be a member of this lobby"
        return is_member


class IsMessageSender(permissions.BasePermission):
    """Permission to check if user is the sender of the message"""
    
    def has_object_permission(self, request, view, obj):
        return (
            request.user 
            and request.user.is_authenticated 
            and obj.sender == request.user
        )


class CanModerateMessage(permissions.BasePermission):
    """Permission to check if user can moderate (delete) messages"""
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        # Message sender can delete their own message
        if obj.sender == request.user:
            return True
        
        # Lobby owner or moderator can delete any message
        try:
            membership = LobbyMembership.objects.get(
                lobby=obj.lobby,
                user=request.user
            )
            return membership.role in ['moderator', 'owner']
        except LobbyMembership.DoesNotExist:
            return False