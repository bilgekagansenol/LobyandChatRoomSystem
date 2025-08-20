from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import authenticate
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.core.cache import cache
from django.utils import timezone

from .models import User, Lobby, LobbyMembership, LobbyBan, Message, LobbyEvent
from .serializers import (
    UserRegistrationSerializer, UserProfileSerializer, LobbyListSerializer,
    LobbyDetailSerializer, LobbyCreateSerializer, LobbyUpdateSerializer,
    MessageSerializer, KickUserSerializer, BanUserSerializer, UnbanUserSerializer,
    ModeratorSerializer, TransferOwnershipSerializer, LobbyEventSerializer
)
from .permissions import (
    IsPremium, IsOwnerOrModerator, IsLobbyOwner, CanJoinLobby,
    IsNotBanned, IsLobbyMember, CanModerateMessage
)


class UserRegistrationView(APIView):
    """User registration endpoint"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(
                {"message": "User created successfully", "user_id": user.id},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(APIView):
    """User profile endpoint"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)
    
    def patch(self, request):
        serializer = UserProfileSerializer(
            request.user, 
            data=request.data, 
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LobbyViewSet(viewsets.ModelViewSet):
    """Lobby CRUD operations"""
    queryset = Lobby.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'list':
            return LobbyListSerializer
        elif self.action == 'create':
            return LobbyCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return LobbyUpdateSerializer
        return LobbyDetailSerializer
    
    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated(), IsPremium()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsLobbyOwner()]
        elif self.action == 'retrieve':
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated()]
    
    def get_queryset(self):
        queryset = Lobby.objects.all()
        
        # Filter parameters
        public_only = self.request.query_params.get('public', None)
        status_filter = self.request.query_params.get('status', None)
        search = self.request.query_params.get('search', None)
        
        if public_only == '1':
            queryset = queryset.filter(is_public=True)
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(owner__username__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        lobby = serializer.save(owner=self.request.user)
        # Create owner membership
        LobbyMembership.objects.create(
            user=self.request.user,
            lobby=lobby,
            role='owner'
        )
        # Log event
        LobbyEvent.objects.create(
            lobby=lobby,
            event_type='status_change',
            actor=self.request.user,
            description=f"Lobby '{lobby.name}' created",
            metadata={'status': 'open'}
        )
    
    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """Join a lobby"""
        lobby = self.get_object()
        
        # Check if can join
        can_join, message = lobby.can_join(request.user)
        if not can_join:
            return Response(
                {"error": message}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create membership
        membership, created = LobbyMembership.objects.get_or_create(
            user=request.user,
            lobby=lobby,
            defaults={'role': 'member'}
        )
        
        if created:
            # Log event
            LobbyEvent.objects.create(
                lobby=lobby,
                event_type='status_change',
                actor=request.user,
                description=f"{request.user.username} joined the lobby"
            )
            return Response({"message": "Joined lobby successfully"})
        
        return Response(
            {"error": "Already in lobby"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """Leave a lobby"""
        lobby = self.get_object()
        
        try:
            membership = LobbyMembership.objects.get(
                user=request.user, 
                lobby=lobby
            )
            
            # Owner cannot leave, must transfer ownership first
            if membership.role == 'owner':
                return Response(
                    {"error": "Owner cannot leave lobby. Transfer ownership first."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            membership.delete()
            
            # Log event
            LobbyEvent.objects.create(
                lobby=lobby,
                event_type='status_change',
                actor=request.user,
                description=f"{request.user.username} left the lobby"
            )
            
            return Response({"message": "Left lobby successfully"})
        
        except LobbyMembership.DoesNotExist:
            return Response(
                {"error": "Not in lobby"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsLobbyOwner])
    def start(self, request, pk=None):
        """Start the game (change status to in_game)"""
        lobby = self.get_object()
        lobby.status = 'in_game'
        lobby.save()
        
        # Log event
        LobbyEvent.objects.create(
            lobby=lobby,
            event_type='status_change',
            actor=request.user,
            description="Game started",
            metadata={'status': 'in_game'}
        )
        
        return Response({"message": "Game started"})
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsLobbyOwner])
    def close(self, request, pk=None):
        """Close the lobby"""
        lobby = self.get_object()
        lobby.status = 'closed'
        lobby.save()
        
        # Log event
        LobbyEvent.objects.create(
            lobby=lobby,
            event_type='status_change',
            actor=request.user,
            description="Lobby closed",
            metadata={'status': 'closed'}
        )
        
        return Response({"message": "Lobby closed"})
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsOwnerOrModerator])
    def kick(self, request, pk=None):
        """Kick a user from lobby"""
        lobby = self.get_object()
        print(f"KICK DEBUG: User {request.user.username} trying to kick from lobby {lobby.id}")
        self.check_object_permissions(request, lobby)
        print(f"KICK DEBUG: Permission check passed")
        serializer = KickUserSerializer(data=request.data)
        
        if serializer.is_valid():
            user_id = serializer.validated_data['user_id']
            reason = serializer.validated_data.get('reason', '')
            
            try:
                user = User.objects.get(id=user_id)
                membership = LobbyMembership.objects.get(user=user, lobby=lobby)
                
                # Cannot kick owner
                if membership.role == 'owner':
                    return Response(
                        {"error": "Cannot kick lobby owner"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                membership.delete()
                
                # Log event
                LobbyEvent.objects.create(
                    lobby=lobby,
                    event_type='kick',
                    actor=request.user,
                    target=user,
                    description=f"{user.username} kicked from lobby. Reason: {reason}",
                    metadata={'reason': reason}
                )
                
                return Response({"message": f"User {user.username} kicked successfully"})
                
            except User.DoesNotExist:
                return Response(
                    {"error": "User not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            except LobbyMembership.DoesNotExist:
                return Response(
                    {"error": "User not in lobby"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsOwnerOrModerator])
    def ban(self, request, pk=None):
        """Ban a user from lobby"""
        lobby = self.get_object()
        self.check_object_permissions(request, lobby)
        serializer = BanUserSerializer(data=request.data)
        
        if serializer.is_valid():
            user_id = serializer.validated_data['user_id']
            reason = serializer.validated_data.get('reason', '')
            
            try:
                user = User.objects.get(id=user_id)
                
                # Cannot ban owner
                if lobby.owner == user:
                    return Response(
                        {"error": "Cannot ban lobby owner"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Remove from lobby if member
                LobbyMembership.objects.filter(user=user, lobby=lobby).delete()
                
                # Create ban record
                ban, created = LobbyBan.objects.get_or_create(
                    lobby=lobby,
                    user=user,
                    defaults={
                        'reason': reason,
                        'banned_by': request.user
                    }
                )
                
                if created:
                    # Log event
                    LobbyEvent.objects.create(
                        lobby=lobby,
                        event_type='ban',
                        actor=request.user,
                        target=user,
                        description=f"{user.username} banned from lobby. Reason: {reason}",
                        metadata={'reason': reason}
                    )
                    
                    return Response({"message": f"User {user.username} banned successfully"})
                else:
                    return Response(
                        {"error": "User already banned"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
            except User.DoesNotExist:
                return Response(
                    {"error": "User not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsOwnerOrModerator])
    def unban(self, request, pk=None):
        """Unban a user from lobby"""
        lobby = self.get_object()
        self.check_object_permissions(request, lobby)
        serializer = UnbanUserSerializer(data=request.data)
        
        if serializer.is_valid():
            user_id = serializer.validated_data['user_id']
            
            try:
                user = User.objects.get(id=user_id)
                ban = LobbyBan.objects.get(lobby=lobby, user=user)
                ban.delete()
                
                # Log event
                LobbyEvent.objects.create(
                    lobby=lobby,
                    event_type='unban',
                    actor=request.user,
                    target=user,
                    description=f"{user.username} unbanned from lobby"
                )
                
                return Response({"message": f"User {user.username} unbanned successfully"})
                
            except User.DoesNotExist:
                return Response(
                    {"error": "User not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            except LobbyBan.DoesNotExist:
                return Response(
                    {"error": "User not banned"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsOwnerOrModerator])
    def add_moderator(self, request, pk=None):
        """Add moderator to lobby"""
        lobby = self.get_object()
        self.check_object_permissions(request, lobby)
        serializer = ModeratorSerializer(data=request.data)
        
        if serializer.is_valid():
            user_id = serializer.validated_data['user_id']
            
            try:
                user = User.objects.get(id=user_id)
                membership = LobbyMembership.objects.get(user=user, lobby=lobby)
                
                if membership.role == 'owner':
                    return Response(
                        {"error": "Owner is already a moderator"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                membership.role = 'moderator'
                membership.save()
                
                # Log event
                LobbyEvent.objects.create(
                    lobby=lobby,
                    event_type='mod_add',
                    actor=request.user,
                    target=user,
                    description=f"{user.username} promoted to moderator"
                )
                
                return Response({"message": f"User {user.username} promoted to moderator"})
                
            except User.DoesNotExist:
                return Response(
                    {"error": "User not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            except LobbyMembership.DoesNotExist:
                return Response(
                    {"error": "User not in lobby"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsOwnerOrModerator])
    def remove_moderator(self, request, pk=None):
        """Remove moderator from lobby"""
        lobby = self.get_object()
        self.check_object_permissions(request, lobby)
        serializer = ModeratorSerializer(data=request.data)
        
        if serializer.is_valid():
            user_id = serializer.validated_data['user_id']
            
            try:
                user = User.objects.get(id=user_id)
                membership = LobbyMembership.objects.get(user=user, lobby=lobby)
                
                if membership.role != 'moderator':
                    return Response(
                        {"error": "User is not a moderator"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                membership.role = 'member'
                membership.save()
                
                # Log event
                LobbyEvent.objects.create(
                    lobby=lobby,
                    event_type='mod_remove',
                    actor=request.user,
                    target=user,
                    description=f"{user.username} demoted from moderator"
                )
                
                return Response({"message": f"User {user.username} demoted from moderator"})
                
            except User.DoesNotExist:
                return Response(
                    {"error": "User not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            except LobbyMembership.DoesNotExist:
                return Response(
                    {"error": "User not in lobby"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsLobbyOwner])
    def transfer_ownership(self, request, pk=None):
        """Transfer ownership of lobby"""
        lobby = self.get_object()
        self.check_object_permissions(request, lobby)
        serializer = TransferOwnershipSerializer(data=request.data)
        
        if serializer.is_valid():
            user_id = serializer.validated_data['user_id']
            
            try:
                user = User.objects.get(id=user_id)
                membership = LobbyMembership.objects.get(user=user, lobby=lobby)
                
                with transaction.atomic():
                    # Update lobby owner
                    old_owner = lobby.owner
                    lobby.owner = user
                    lobby.save()
                    
                    # Update memberships
                    old_owner_membership = LobbyMembership.objects.get(
                        user=old_owner, 
                        lobby=lobby
                    )
                    old_owner_membership.role = 'member'
                    old_owner_membership.save()
                    
                    membership.role = 'owner'
                    membership.save()
                    
                    # Log event
                    LobbyEvent.objects.create(
                        lobby=lobby,
                        event_type='transfer',
                        actor=request.user,
                        target=user,
                        description=f"Ownership transferred to {user.username}"
                    )
                
                return Response({"message": f"Ownership transferred to {user.username}"})
                
            except User.DoesNotExist:
                return Response(
                    {"error": "User not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            except LobbyMembership.DoesNotExist:
                return Response(
                    {"error": "User not in lobby"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MessageViewSet(viewsets.ModelViewSet):
    """Message CRUD operations"""
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        lobby_id = self.kwargs.get('lobby_pk')
        if lobby_id:
            return Message.objects.filter(
                lobby_id=lobby_id,
                is_deleted=False
            ).order_by('-created_at')
        return Message.objects.none()
    
    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), CanModerateMessage()]
        return [permissions.IsAuthenticated(), IsLobbyMember()]
    
    def perform_create(self, serializer):
        lobby_id = self.kwargs.get('lobby_pk')
        lobby = get_object_or_404(Lobby, id=lobby_id)
        
        # Check if user is member
        if not LobbyMembership.objects.filter(
            user=self.request.user, 
            lobby=lobby
        ).exists():
            raise permissions.PermissionDenied("Must be lobby member to send messages")
        
        serializer.save(sender=self.request.user, lobby=lobby)
    
    def perform_destroy(self, instance):
        # Soft delete
        instance.is_deleted = True
        instance.save()
