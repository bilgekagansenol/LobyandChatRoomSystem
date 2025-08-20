# Premium Chat Lobby

A Django-based real-time chat lobby system similar to Haxball, where premium users can create lobbies and all users can join and chat via WebSocket connections.

## Features

- **Premium Lobby Creation**: Only premium users can create chat lobbies
- **Real-time Chat**: WebSocket-based messaging with presence indicators
- **Moderation System**: Kick, ban, and moderator management
- **Rate Limiting**: Anti-spam protection (3 messages per 2 seconds)
- **JWT Authentication**: Secure API and WebSocket authentication
- **Admin Panel**: Complete administrative interface
- **Comprehensive API**: REST endpoints for all operations

## Tech Stack

- **Backend**: Django 4.2 + Django REST Framework
- **Real-time**: Django Channels 4 + Redis
- **Database**: SQLite (dev) / PostgreSQL (production)
- **Authentication**: Django REST Framework SimpleJWT
- **Cache/Queue**: Redis
- **Testing**: pytest + pytest-django

## Quick Start

### Prerequisites

- Python 3.8+
- Redis server
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd backendpande
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env file with your settings
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Seed demo data** (optional)
   ```bash
   python manage.py seed_demo
   ```

8. **Start Redis server**
   ```bash
   redis-server
   ```

9. **Run development server**
   ```bash
   python manage.py runserver
   ```

The API will be available at `http://localhost:8000/api/`

### Using Make (Recommended)

```bash
# Install dependencies and run migrations
make install
make migrate

# Seed demo data
make seed

# Start development server (includes Redis check)
make dev
```

## Docker Setup

1. **Build and start containers**
   ```bash
   docker-compose up --build
   ```

2. **Access the application**
   - API: `http://localhost:8000/api/`
   - Admin: `http://localhost:8000/admin/`
   - WebSocket: `ws://localhost:8000/ws/lobbies/{lobby_id}/`

## API Documentation

### Authentication

#### Register User
```http
POST /api/auth/register/
Content-Type: application/json

{
  "username": "newuser",
  "email": "user@example.com", 
  "password": "securepass123",
  "password_confirm": "securepass123"
}
```

#### Login
```http
POST /api/auth/login/
Content-Type: application/json

{
  "username": "username",
  "password": "password"
}
```

Response:
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### User Profile

#### Get Profile
```http
GET /api/me/
Authorization: Bearer <access_token>
```

### Lobbies

#### List Lobbies
```http
GET /api/lobbies/?public=1&status=open&search=gaming
Authorization: Bearer <access_token>
```

#### Create Lobby (Premium Only)
```http
POST /api/lobbies/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "My Gaming Lobby",
  "is_public": true,
  "max_participants": 8
}
```

#### Join Lobby
```http
POST /api/lobbies/{id}/join/
Authorization: Bearer <access_token>
```

#### Leave Lobby
```http
POST /api/lobbies/{id}/leave/
Authorization: Bearer <access_token>
```

#### Start Game (Owner Only)
```http
POST /api/lobbies/{id}/start/
Authorization: Bearer <access_token>
```

#### Kick User (Owner/Moderator)
```http
POST /api/lobbies/{id}/kick/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "user_id": 123,
  "reason": "Inappropriate behavior"
}
```

#### Ban User (Owner/Moderator)
```http
POST /api/lobbies/{id}/ban/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "user_id": 123,
  "reason": "Repeated violations"
}
```

### Messages

#### List Messages
```http
GET /api/lobbies/{lobby_id}/messages/
Authorization: Bearer <access_token>
```

#### Send Message
```http
POST /api/lobbies/{lobby_id}/messages/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "content": "Hello everyone!"
}
```

## WebSocket Usage

### Connection

Connect to: `ws://localhost:8000/ws/lobbies/{lobby_id}/?token={jwt_token}`

### Message Types

#### Send Chat Message
```json
{
  "type": "chat_message",
  "message": "Hello world!"
}
```

#### Start Typing
```json
{
  "type": "typing_start"
}
```

#### Stop Typing  
```json
{
  "type": "typing_stop"
}
```

### Received Events

#### Chat Message
```json
{
  "type": "chat_message",
  "message": {
    "id": 1,
    "content": "Hello world!",
    "sender": {
      "id": 1,
      "username": "user1",
      "is_premium": false
    },
    "created_at": "2024-01-01T12:00:00Z"
  }
}
```

#### User Joined
```json
{
  "type": "presence_join",
  "user_id": 1,
  "username": "user1",
  "is_premium": false
}
```

#### User Left
```json
{
  "type": "presence_leave", 
  "user_id": 1,
  "username": "user1"
}
```

#### Typing Events
```json
{
  "type": "typing_start",
  "user_id": 1,
  "username": "user1"
}
```

#### Moderation Events
```json
{
  "type": "moderation_kick",
  "target_id": 1,
  "target_username": "user1",
  "reason": "Rule violation"
}
```

## Demo Data

The system includes demo data with:
- 2 premium users: `premium_user_1`, `premium_user_2`
- 5 normal users: `user_1` to `user_5`
- 3 sample lobbies with members and messages
- Password for all demo users: `testpass123`

Load demo data:
```bash
python manage.py seed_demo --clear
```

## Testing

Run the test suite:
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=chat

# Run specific test class
pytest chat/tests.py::LobbyAPITest

# Run with output
pytest -v -s
```

## Admin Interface

Access the admin panel at `http://localhost:8000/admin/` with superuser credentials.

Features:
- User management with premium status toggle
- Lobby monitoring and moderation
- Message moderation
- Ban management
- Event logging review

## Project Structure

```
premiumchat/
├── chat/                          # Main app
│   ├── models.py                  # Data models
│   ├── views.py                   # API views
│   ├── serializers.py             # DRF serializers
│   ├── permissions.py             # Custom permissions
│   ├── consumers.py               # WebSocket consumers
│   ├── routing.py                 # WebSocket routing
│   ├── middleware.py              # JWT WebSocket middleware
│   ├── admin.py                   # Admin configuration
│   ├── tests.py                   # Test suite
│   └── management/commands/
│       └── seed_demo.py           # Demo data command
├── premiumchat/                   # Django project
│   ├── settings.py                # Django settings
│   ├── urls.py                    # URL routing
│   └── asgi.py                    # ASGI configuration
├── requirements.txt               # Python dependencies
├── docker-compose.yml             # Docker setup
├── Dockerfile                     # Docker image
├── Makefile                       # Development commands
└── README.md                      # This file
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | Required |
| `DEBUG` | Debug mode | `True` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `DATABASE_URL` | Database URL | `sqlite:///db.sqlite3` |
| `ALLOWED_HOSTS` | Allowed hosts | `localhost,127.0.0.1` |

## Demo Credentials

Default demo users (created with `python manage.py seed_demo`):

**Premium Users:**
- Username: `premium_user_1` / Password: `testpass123`
- Username: `premium_user_2` / Password: `testpass123`

**Normal Users:**
- Username: `user_1` to `user_5` / Password: `testpass123`

## License

This project is licensed under the MIT License.
