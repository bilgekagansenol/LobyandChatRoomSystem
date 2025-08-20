from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import UserRegistrationView, UserProfileView, LobbyViewSet, MessageViewSet

# Main router
router = DefaultRouter()
router.register(r'lobbies', LobbyViewSet)

urlpatterns = [
    # Authentication
    path('auth/register/', UserRegistrationView.as_view(), name='register'),
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # User profile
    path('me/', UserProfileView.as_view(), name='user_profile'),
    
    # Lobby messages (manual routing)
    path('lobbies/<int:lobby_pk>/messages/', MessageViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='lobby-messages-list'),
    path('lobbies/<int:lobby_pk>/messages/<int:pk>/', MessageViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='lobby-messages-detail'),
    
    # API routes
    path('', include(router.urls)),
]