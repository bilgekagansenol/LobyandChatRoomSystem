from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, Lobby, LobbyMembership, LobbyBan, Message, LobbyEvent


class UserRegistrationSerializer(serializers.ModelSerializer):
    """User registration serializer"""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password_confirm')

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """User profile serializer"""
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'is_premium', 'created_at')
        read_only_fields = ('id', 'is_premium', 'created_at')


class UserSerializer(serializers.ModelSerializer):
    """Basic user serializer for listing"""
    class Meta:
        model = User
        fields = ('id', 'username', 'is_premium')


class LobbyMembershipSerializer(serializers.ModelSerializer):
    """Lobby membership serializer"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = LobbyMembership
        fields = ('user', 'role', 'joined_at')


class LobbyBanSerializer(serializers.ModelSerializer):
    """Lobby ban serializer"""
    user = UserSerializer(read_only=True)
    banned_by = UserSerializer(read_only=True)
    
    class Meta:
        model = LobbyBan
        fields = ('user', 'reason', 'banned_by', 'created_at')


class MessageSerializer(serializers.ModelSerializer):
    """Message serializer"""
    sender = UserSerializer(read_only=True)
    
    class Meta:
        model = Message
        fields = ('id', 'sender', 'content', 'created_at', 'is_deleted')
        read_only_fields = ('id', 'sender', 'created_at')

    def validate_content(self, value):
        if len(value.strip()) == 0:
            raise serializers.ValidationError("Message cannot be empty")
        return value.strip()


class LobbyListSerializer(serializers.ModelSerializer):
    """Lobby list serializer"""
    owner = UserSerializer(read_only=True)
    current_participants_count = serializers.ReadOnlyField()
    is_full = serializers.ReadOnlyField()
    
    class Meta:
        model = Lobby
        fields = (
            'id', 'name', 'owner', 'is_public', 'status', 
            'max_participants', 'current_participants_count', 
            'is_full', 'created_at'
        )


class LobbyDetailSerializer(serializers.ModelSerializer):
    """Lobby detail serializer"""
    owner = UserSerializer(read_only=True)
    memberships = LobbyMembershipSerializer(many=True, read_only=True)
    current_participants_count = serializers.ReadOnlyField()
    is_full = serializers.ReadOnlyField()
    recent_messages = serializers.SerializerMethodField()
    
    class Meta:
        model = Lobby
        fields = (
            'id', 'name', 'owner', 'is_public', 'status', 
            'max_participants', 'current_participants_count', 
            'is_full', 'memberships', 'recent_messages',
            'created_at', 'updated_at'
        )
    
    def get_recent_messages(self, obj):
        recent_messages = obj.messages.filter(is_deleted=False)[:50]
        return MessageSerializer(recent_messages, many=True).data


class LobbyCreateSerializer(serializers.ModelSerializer):
    """Lobby creation serializer"""
    class Meta:
        model = Lobby
        fields = ('name', 'is_public', 'max_participants')
    
    def validate_name(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Lobby name must be at least 3 characters long")
        return value.strip()
    
    def validate_max_participants(self, value):
        if value < 2 or value > 50:
            raise serializers.ValidationError("Max participants must be between 2 and 50")
        return value


class LobbyUpdateSerializer(serializers.ModelSerializer):
    """Lobby update serializer"""
    class Meta:
        model = Lobby
        fields = ('name', 'status', 'max_participants')
    
    def validate_name(self, value):
        if value and len(value.strip()) < 3:
            raise serializers.ValidationError("Lobby name must be at least 3 characters long")
        return value.strip() if value else value
    
    def validate_max_participants(self, value):
        if value and (value < 2 or value > 50):
            raise serializers.ValidationError("Max participants must be between 2 and 50")
        return value


class KickUserSerializer(serializers.Serializer):
    """Kick user serializer"""
    user_id = serializers.IntegerField()
    reason = serializers.CharField(required=False, allow_blank=True, max_length=500)
    
    def validate_user_id(self, value):
        try:
            User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found")
        return value


class BanUserSerializer(serializers.Serializer):
    """Ban user serializer"""
    user_id = serializers.IntegerField()
    reason = serializers.CharField(required=False, allow_blank=True, max_length=500)
    
    def validate_user_id(self, value):
        try:
            User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found")
        return value


class UnbanUserSerializer(serializers.Serializer):
    """Unban user serializer"""
    user_id = serializers.IntegerField()
    
    def validate_user_id(self, value):
        try:
            User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found")
        return value


class ModeratorSerializer(serializers.Serializer):
    """Add/Remove moderator serializer"""
    user_id = serializers.IntegerField()
    
    def validate_user_id(self, value):
        try:
            User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found")
        return value


class TransferOwnershipSerializer(serializers.Serializer):
    """Transfer ownership serializer"""
    user_id = serializers.IntegerField()
    
    def validate_user_id(self, value):
        try:
            User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found")
        return value


class LobbyEventSerializer(serializers.ModelSerializer):
    """Lobby event serializer"""
    actor = UserSerializer(read_only=True)
    target = UserSerializer(read_only=True)
    
    class Meta:
        model = LobbyEvent
        fields = ('event_type', 'actor', 'target', 'description', 'metadata', 'created_at')