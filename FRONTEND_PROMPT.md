# React Frontend for Django Premium Chat Lobby System

## 🎯 Project Requirements
Create a complete React.js frontend for the Django Premium Chat Lobby system with real-time chat, premium user features, and comprehensive moderation interface.

## 🏗️ Technical Stack
- **Framework**: React.js (functional components with hooks)
- **Styling**: Tailwind CSS or Material-UI
- **HTTP Client**: Axios for API calls
- **WebSocket**: Socket.IO or native WebSocket for real-time chat
- **State Management**: React Context API or Redux Toolkit
- **Authentication**: JWT token management
- **Routing**: React Router v6

## 🔌 Backend API Integration

### Base Configuration
```javascript
const API_BASE_URL = 'http://localhost:8001/api';
```

### Authentication Endpoints
```javascript
// Register new user
POST /api/auth/register/
Body: { username, email, password, password_confirm }
Response: { message, user_id }

// Login user  
POST /api/auth/login/
Body: { username, password }
Response: { access, refresh }

// Refresh token
POST /api/auth/refresh/
Body: { refresh }
Response: { access, refresh }
```

### User Profile Endpoints
```javascript
// Get current user profile
GET /api/me/
Headers: { Authorization: 'Bearer <access_token>' }
Response: { id, username, email, is_premium, created_at }

// Update profile
PATCH /api/me/
Headers: { Authorization: 'Bearer <access_token>' }
Body: { email }
Response: { id, username, email, is_premium, created_at }
```

### Lobby Management Endpoints
```javascript
// List all lobbies with filters
GET /api/lobbies/?search=gaming&public=1&status=open
Headers: { Authorization: 'Bearer <access_token>' }
Response: { count, results: [{ id, name, owner, is_public, status, max_participants, current_participants_count }] }

// Create new lobby (Premium users only)
POST /api/lobbies/
Headers: { Authorization: 'Bearer <access_token>' }
Body: { name, is_public, max_participants }
Response: { id, name, is_public, max_participants }

// Get lobby details
GET /api/lobbies/{lobby_id}/
Response: { id, name, owner, memberships, recent_messages, ... }

// Update lobby (Owner only)
PATCH /api/lobbies/{lobby_id}/
Body: { name, max_participants }
```

### Lobby Actions
```javascript
// Join lobby
POST /api/lobbies/{lobby_id}/join/
Response: { message }

// Leave lobby
POST /api/lobbies/{lobby_id}/leave/
Response: { message }

// Start game (Owner only)
POST /api/lobbies/{lobby_id}/start/
Response: { message }

// Close lobby (Owner only)
POST /api/lobbies/{lobby_id}/close/
Response: { message }
```

### Moderation Endpoints (Owner/Moderator only)
```javascript
// Kick user
POST /api/lobbies/{lobby_id}/kick/
Body: { user_id, reason }
Response: { message }

// Ban user
POST /api/lobbies/{lobby_id}/ban/
Body: { user_id, reason }
Response: { message }

// Unban user
POST /api/lobbies/{lobby_id}/unban/
Body: { user_id }
Response: { message }

// Add moderator
POST /api/lobbies/{lobby_id}/add_moderator/
Body: { user_id }
Response: { message }

// Remove moderator  
POST /api/lobbies/{lobby_id}/remove_moderator/
Body: { user_id }
Response: { message }

// Transfer ownership
POST /api/lobbies/{lobby_id}/transfer_ownership/
Body: { user_id }
Response: { message }
```

### Message Endpoints
```javascript
// Get lobby messages
GET /api/lobbies/{lobby_id}/messages/
Response: { count, results: [{ id, sender, content, created_at, is_deleted }] }

// Send message
POST /api/lobbies/{lobby_id}/messages/
Body: { content }
Response: { id, sender, content, created_at }

// Delete message (Soft delete)
DELETE /api/lobbies/{lobby_id}/messages/{message_id}/
Response: 204 No Content
```

## 📱 Required Components & Features

### 1. Authentication System
- **LoginPage** - Login form with JWT token storage
- **RegisterPage** - User registration form
- **ProtectedRoute** - Route guard for authenticated users
- **PremiumRoute** - Route guard for premium users only
- **TokenManager** - Auto refresh expired tokens

### 2. Dashboard & Navigation
- **Header** - User profile, premium status, logout
- **Sidebar** - Navigation menu (Lobbies, Profile, Settings)
- **LobbyList** - Display all lobbies with filters
- **SearchBar** - Search lobbies by name
- **FilterControls** - Filter by public/private, status, etc.

### 3. Lobby Management
- **CreateLobbyModal** - Premium users create new lobbies
- **LobbyCard** - Display lobby info (name, participants, status)
- **LobbyDetails** - Full lobby view with members and messages
- **JoinLeaveButton** - Join/leave lobby functionality
- **LobbySettings** - Owner settings (name, max participants, etc.)

### 4. Real-time Chat System
- **ChatWindow** - Main chat interface
- **MessageList** - Display all messages with pagination
- **MessageInput** - Send new messages (with rate limiting UI)
- **MessageItem** - Individual message component
- **TypingIndicator** - Show who's typing
- **OnlineUsersList** - Show online members

### 5. Moderation Interface
- **ModerationPanel** - Owner/moderator controls
- **UserList** - List of lobby members with roles
- **KickBanModal** - Kick/ban user with reason
- **ModeratorControls** - Add/remove moderators
- **OwnershipTransfer** - Transfer lobby ownership

### 6. User Experience Features
- **PremiumBadge** - Show premium status
- **RoleIndicator** - Show user roles (Owner, Moderator, Member)
- **NotificationSystem** - Real-time notifications for lobby events
- **LoadingStates** - Loading spinners for API calls
- **ErrorHandling** - User-friendly error messages
- **ResponsiveDesign** - Mobile-friendly interface

## 🔄 WebSocket Implementation

### Connection Setup
```javascript
const wsUrl = 'ws://localhost:8001/ws/lobby/{lobby_id}/';
// Include JWT token in connection headers
```

### WebSocket Events to Handle
- **message.new** - New chat message received
- **user.joined** - User joined lobby
- **user.left** - User left lobby  
- **user.kicked** - User was kicked
- **user.banned** - User was banned
- **game.started** - Game status changed
- **lobby.closed** - Lobby was closed
- **user.typing** - User typing indicator

## 🎨 UI/UX Design Requirements

### Design Theme: Gaming/Modern
- **Color Scheme**: Dark theme with accent colors (blue/purple)
- **Typography**: Modern, readable fonts
- **Icons**: Gaming-related icons (FontAwesome or Heroicons)
- **Layout**: Clean, intuitive navigation
- **Responsive**: Mobile-first design approach

### Key UI Elements
1. **Premium User Badge** - Golden/VIP styling
2. **Role Indicators** - Different colors for Owner/Moderator/Member
3. **Online Status** - Green dot for online users
4. **Message Status** - Sent/delivered indicators
5. **Rate Limit Indicator** - Show message cooldown
6. **Lobby Status Icons** - Open/In Game/Closed states

## 🔐 Authentication Flow

### JWT Token Management
1. Store tokens in localStorage/sessionStorage
2. Auto-refresh tokens before expiry
3. Redirect to login on authentication errors
4. Include Bearer token in all API requests

### Permission-based Rendering
```javascript
// Example: Show create lobby button only for premium users
{user.is_premium && <CreateLobbyButton />}

// Show moderation controls only for owners/moderators  
{(userRole === 'owner' || userRole === 'moderator') && <ModerationPanel />}
```

## 📊 State Management Structure

### Global Context/Store
```javascript
// AuthContext - User authentication state
// LobbyContext - Current lobby state  
// ChatContext - Chat messages and WebSocket connection
// UIContext - Loading states, modals, notifications
```

### Required State
- **User**: `{ id, username, email, is_premium, token }`
- **CurrentLobby**: `{ id, name, members, messages, userRole }`
- **Lobbies**: `[{ id, name, participants_count, status }]`
- **Chat**: `{ messages: [], typing: [], onlineUsers: [] }`

## 🧪 Testing Requirements

### Key Flows to Test
1. **Premium User Flow**: Login → Create Lobby → Manage Settings → Moderate
2. **Normal User Flow**: Login → Join Lobby → Send Messages → Leave
3. **Moderation Flow**: Kick User → Ban User → Add Moderator → Transfer Ownership
4. **Real-time Flow**: Multiple users chatting simultaneously
5. **Permission Testing**: Non-premium trying to create lobby (should fail)

## 🚀 Deployment Considerations

### Environment Configuration
- Development: `API_URL=http://localhost:8001`
- Production: `API_URL=https://your-api-domain.com`
- WebSocket URLs for different environments

### Performance Optimizations
- **Code Splitting**: Lazy load components
- **Message Pagination**: Load messages on scroll
- **WebSocket Reconnection**: Handle connection drops
- **Caching**: Cache lobby list and user data
- **Debouncing**: Search and typing indicators

## 📋 Implementation Priority

### Phase 1: Core Features
1. Authentication (Login/Register)
2. Lobby List & Details
3. Basic Chat Interface
4. Join/Leave Functionality

### Phase 2: Premium Features  
1. Create Lobby (Premium only)
2. Lobby Settings Management
3. Real-time WebSocket Chat
4. User Role System

### Phase 3: Advanced Features
1. Full Moderation Interface
2. Advanced Search & Filters
3. Notification System
4. Mobile Responsiveness

### Phase 4: Polish & Optimization
1. Performance Optimization
2. Error Handling Enhancement
3. Loading States & Animations
4. Comprehensive Testing

## 🎯 Success Criteria

The frontend should provide:
- ✅ Seamless authentication with JWT
- ✅ Real-time chat experience
- ✅ Premium user lobby creation
- ✅ Complete moderation interface
- ✅ Responsive design for all devices
- ✅ Proper error handling and user feedback
- ✅ Performance optimized for scalability

This frontend will create a complete gaming lobby experience similar to Haxball, with premium features and comprehensive chat moderation capabilities.