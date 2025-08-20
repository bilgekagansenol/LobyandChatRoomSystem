from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Lobby, LobbyMembership, LobbyBan, Message, LobbyEvent


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """User admin with premium status"""
    list_display = ('username', 'email', 'is_premium', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('is_premium', 'is_staff', 'is_active', 'date_joined')
    search_fields = ('username', 'email')
    ordering = ('-date_joined',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Premium Status', {'fields': ('is_premium',)}),
    )
    
    actions = ['make_premium', 'remove_premium']
    
    def make_premium(self, request, queryset):
        updated = queryset.update(is_premium=True)
        self.message_user(request, f'{updated} users marked as premium.')
    make_premium.short_description = "Mark selected users as premium"
    
    def remove_premium(self, request, queryset):
        updated = queryset.update(is_premium=False)
        self.message_user(request, f'{updated} users premium status removed.')
    remove_premium.short_description = "Remove premium status"


class LobbyMembershipInline(admin.TabularInline):
    """Inline for lobby memberships"""
    model = LobbyMembership
    extra = 0
    readonly_fields = ('joined_at',)


class LobbyBanInline(admin.TabularInline):
    """Inline for lobby bans"""
    model = LobbyBan
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(Lobby)
class LobbyAdmin(admin.ModelAdmin):
    """Lobby admin"""
    list_display = ('name', 'owner', 'status', 'is_public', 'current_participants_count', 'max_participants', 'created_at')
    list_filter = ('status', 'is_public', 'created_at')
    search_fields = ('name', 'owner__username')
    readonly_fields = ('created_at', 'updated_at', 'current_participants_count')
    ordering = ('-created_at',)
    
    inlines = [LobbyMembershipInline, LobbyBanInline]
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'owner', 'is_public')
        }),
        ('Settings', {
            'fields': ('status', 'max_participants')
        }),
        ('Statistics', {
            'fields': ('current_participants_count',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(LobbyMembership)
class LobbyMembershipAdmin(admin.ModelAdmin):
    """Lobby membership admin"""
    list_display = ('user', 'lobby', 'role', 'joined_at')
    list_filter = ('role', 'joined_at')
    search_fields = ('user__username', 'lobby__name')
    readonly_fields = ('joined_at',)
    ordering = ('-joined_at',)


@admin.register(LobbyBan)
class LobbyBanAdmin(admin.ModelAdmin):
    """Lobby ban admin"""
    list_display = ('user', 'lobby', 'banned_by', 'created_at', 'reason_preview')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'lobby__name', 'banned_by__username')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    
    def reason_preview(self, obj):
        if obj.reason:
            return obj.reason[:50] + '...' if len(obj.reason) > 50 else obj.reason
        return '-'
    reason_preview.short_description = 'Reason'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Message admin"""
    list_display = ('sender', 'lobby', 'content_preview', 'created_at', 'is_deleted')
    list_filter = ('is_deleted', 'created_at')
    search_fields = ('sender__username', 'lobby__name', 'content')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    
    actions = ['mark_deleted', 'mark_not_deleted']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'
    
    def mark_deleted(self, request, queryset):
        updated = queryset.update(is_deleted=True)
        self.message_user(request, f'{updated} messages marked as deleted.')
    mark_deleted.short_description = "Mark selected messages as deleted"
    
    def mark_not_deleted(self, request, queryset):
        updated = queryset.update(is_deleted=False)
        self.message_user(request, f'{updated} messages restored.')
    mark_not_deleted.short_description = "Restore selected messages"


@admin.register(LobbyEvent)
class LobbyEventAdmin(admin.ModelAdmin):
    """Lobby event admin"""
    list_display = ('lobby', 'event_type', 'actor', 'target', 'created_at', 'description_preview')
    list_filter = ('event_type', 'created_at')
    search_fields = ('lobby__name', 'actor__username', 'target__username', 'description')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    
    def description_preview(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_preview.short_description = 'Description'


# Customize admin site
admin.site.site_header = "Premium Chat Lobby Administration"
admin.site.site_title = "Premium Chat Admin"
admin.site.index_title = "Welcome to Premium Chat Administration"
