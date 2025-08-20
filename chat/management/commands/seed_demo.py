import random
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from chat.models import Lobby, LobbyMembership, Message, LobbyBan, LobbyEvent

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed database with demo data: 2 premium users, 5 normal users, 3 lobbies, 40 messages'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            Message.objects.all().delete()
            LobbyBan.objects.all().delete()
            LobbyMembership.objects.all().delete()
            LobbyEvent.objects.all().delete()
            Lobby.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()
            self.stdout.write(self.style.SUCCESS('Existing data cleared.'))

        # Create users
        self.stdout.write('Creating users...')
        
        # Premium users
        premium_users = []
        for i in range(1, 3):
            user = User.objects.create_user(
                username=f'premium_user_{i}',
                email=f'premium{i}@example.com',
                password='testpass123',
                is_premium=True
            )
            premium_users.append(user)
            self.stdout.write(f'Created premium user: {user.username}')

        # Normal users
        normal_users = []
        for i in range(1, 6):
            user = User.objects.create_user(
                username=f'user_{i}',
                email=f'user{i}@example.com',
                password='testpass123',
                is_premium=False
            )
            normal_users.append(user)
            self.stdout.write(f'Created normal user: {user.username}')

        all_users = premium_users + normal_users

        # Create lobbies
        self.stdout.write('Creating lobbies...')
        
        lobby_data = [
            {
                'name': 'Gaming Lounge',
                'owner': premium_users[0],
                'is_public': True,
                'status': 'open',
                'max_participants': 8
            },
            {
                'name': 'VIP Room',
                'owner': premium_users[1],
                'is_public': False,
                'status': 'open',
                'max_participants': 4
            },
            {
                'name': 'General Chat',
                'owner': premium_users[0],
                'is_public': True,
                'status': 'in_game',
                'max_participants': 12
            }
        ]

        lobbies = []
        for data in lobby_data:
            lobby = Lobby.objects.create(**data)
            lobbies.append(lobby)
            
            # Create owner membership
            LobbyMembership.objects.create(
                user=data['owner'],
                lobby=lobby,
                role='owner'
            )
            
            # Create event
            LobbyEvent.objects.create(
                lobby=lobby,
                event_type='status_change',
                actor=data['owner'],
                description=f"Lobby '{lobby.name}' created",
                metadata={'status': lobby.status}
            )
            
            self.stdout.write(f'Created lobby: {lobby.name}')

        # Add random members to lobbies
        self.stdout.write('Adding members to lobbies...')
        
        for lobby in lobbies:
            # Add 2-4 random members to each lobby
            members_to_add = random.sample(normal_users, random.randint(2, 4))
            
            for user in members_to_add:
                if not LobbyMembership.objects.filter(user=user, lobby=lobby).exists():
                    role = 'moderator' if random.random() < 0.3 else 'member'
                    LobbyMembership.objects.create(
                        user=user,
                        lobby=lobby,
                        role=role
                    )
                    
                    # Create join event
                    LobbyEvent.objects.create(
                        lobby=lobby,
                        event_type='status_change',
                        actor=user,
                        description=f"{user.username} joined the lobby"
                    )
                    
                    if role == 'moderator':
                        LobbyEvent.objects.create(
                            lobby=lobby,
                            event_type='mod_add',
                            actor=lobby.owner,
                            target=user,
                            description=f"{user.username} promoted to moderator"
                        )

        # Create some bans
        self.stdout.write('Creating some bans...')
        
        # Ban one user from a lobby
        banned_user = normal_users[-1]
        ban_lobby = lobbies[0]
        
        # Remove from lobby if member
        LobbyMembership.objects.filter(user=banned_user, lobby=ban_lobby).delete()
        
        LobbyBan.objects.create(
            lobby=ban_lobby,
            user=banned_user,
            reason="Inappropriate behavior",
            banned_by=ban_lobby.owner
        )
        
        LobbyEvent.objects.create(
            lobby=ban_lobby,
            event_type='ban',
            actor=ban_lobby.owner,
            target=banned_user,
            description=f"{banned_user.username} banned from lobby. Reason: Inappropriate behavior",
            metadata={'reason': 'Inappropriate behavior'}
        )

        # Create messages
        self.stdout.write('Creating messages...')
        
        sample_messages = [
            "Hello everyone!",
            "How's everyone doing?",
            "Ready to start the game?",
            "This lobby is awesome!",
            "Anyone want to team up?",
            "Great game last time",
            "What's the plan?",
            "Let's do this!",
            "GG everyone",
            "See you next time",
            "Nice play!",
            "That was close",
            "Well played",
            "Thanks for the game",
            "Looking forward to the next match",
        ]
        
        message_count = 0
        for lobby in lobbies:
            # Get lobby members
            members = [membership.user for membership in lobby.memberships.all()]
            
            if not members:
                continue
                
            # Create 10-15 messages per lobby
            num_messages = random.randint(10, 15)
            
            for _ in range(num_messages):
                sender = random.choice(members)
                content = random.choice(sample_messages)
                
                # Add some variation to messages
                if random.random() < 0.3:
                    content += f" @{random.choice(members).username}"
                
                Message.objects.create(
                    lobby=lobby,
                    sender=sender,
                    content=content
                )
                
                message_count += 1

        # Create summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write('DEMO DATA SEEDED SUCCESSFULLY')
        self.stdout.write('='*50)
        self.stdout.write(f'Premium users created: {len(premium_users)}')
        self.stdout.write(f'Normal users created: {len(normal_users)}')
        self.stdout.write(f'Lobbies created: {len(lobbies)}')
        self.stdout.write(f'Messages created: {message_count}')
        self.stdout.write(f'Bans created: {LobbyBan.objects.count()}')
        self.stdout.write(f'Events logged: {LobbyEvent.objects.count()}')
        self.stdout.write('\nDefault credentials:')
        self.stdout.write('Premium users: premium_user_1, premium_user_2 (password: testpass123)')
        self.stdout.write('Normal users: user_1 to user_5 (password: testpass123)')
        self.stdout.write('\nYou can now test the API endpoints and WebSocket connections!')
        self.stdout.write('='*50)