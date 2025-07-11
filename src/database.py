"""
Redis database manager for calendar data storage.

This module implements the "Repository Pattern" for data access.
All database operations are centralized here, making it easy to:
- Change database implementations later
- Add caching or optimization
- Handle data serialization/deserialization
- Maintain data consistency

Why Redis?
- Fast in-memory storage (perfect for generated data)
- Built-in data structures (sets, hashes)
- Easy to set up for development
- Can export data to files easily
- Good for prototyping and research

Architecture Pattern: Repository + Data Access Layer
- Abstracts database operations from business logic
- Handles data serialization (Python objects ↔ Redis)
- Provides indexing for fast lookups
"""

import json
import redis
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from .data_models import User, CalendarEvent, GenerationStats, GenerationBatch


class RedisManager:
    """
    Manages Redis database operations for calendar data (Repository Pattern).
    
    This class implements the Repository pattern for data persistence.
    It handles all CRUD operations and data serialization.
    
    Redis Data Structure Design:
    - user:{user_id} → Hash containing user data
    - event:{event_id} → Hash containing event data  
    - users → Set of all user IDs (for indexing)
    - events → Set of all event IDs (for indexing)
    - user_events:{user_id} → Set of event IDs for that user
    
    Why this structure?
    - Fast lookups by ID (O(1) operations)
    - Easy to get all users/events
    - Efficient user→events relationships
    - Memory efficient for Redis
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Redis connection with configuration.
        
        The initialization follows the "fail-fast" principle - if Redis
        is not available, the application stops immediately rather than
        failing later during operations.
        
        Args:
            config: Redis configuration dictionary containing:
                   - host: Redis server hostname
                   - port: Redis server port  
                   - db: Database number (0-15)
                   - password: Redis password (if any)
                   - decode_responses: Auto-decode bytes to strings
                   
        Raises:
            redis.ConnectionError: If can't connect to Redis server
        """
        self.config = config
        
        # Create Redis client with configuration
        # decode_responses=True automatically converts bytes to strings
        self.client = redis.Redis(
            host=config.get('host', 'localhost'),      # Default to localhost
            port=config.get('port', 6379),             # Default Redis port
            db=config.get('db', 0),                    # Database 0 (Redis has 16 databases)
            password=config.get('password'),           # Optional password
            decode_responses=config.get('decode_responses', True)  # Auto-decode responses
        )
        
        # Test connection immediately - "fail fast" principle
        # Better to know now if Redis is unavailable than fail during operations
        try:
            self.client.ping()  # Simple test command
            print(" Connected to Redis successfully")
        except redis.ConnectionError as e:
            print(f" Failed to connect to Redis: {e}")
            raise  # Re-raise exception to stop application startup
    
    def _generate_id(self, prefix: str = "") -> str:
        """Generate unique ID with optional prefix."""
        return f"{prefix}{uuid.uuid4().hex[:8]}" if prefix else uuid.uuid4().hex[:8]
    
    # User operations
    def save_user(self, user: User) -> User:
        """Save a user to Redis.
        
        Args:
            user: User object to save
            
        Returns:
            User object with generated ID
        """
        if not user.user_id:
            user.user_id = self._generate_id("user_")
        
        if not user.created_at:
            user.created_at = datetime.now()
        
        # Store user data
        user_key = f"user:{user.user_id}"
        user_data = user.dict()
        
        # Prepare data for Redis (filter out None values and convert properly)
        redis_data = {}
        for k, v in user_data.items():
            if v is not None:  # Skip None values
                if isinstance(v, (dict, list)):
                    redis_data[k] = json.dumps(v)
                elif isinstance(v, datetime):
                    redis_data[k] = v.isoformat()
                else:
                    redis_data[k] = str(v)
        
        if redis_data:  # Only call hset if we have data
            # Redis 3.x compatible version (no mapping parameter)
            for field, value in redis_data.items():
                self.client.hset(user_key, field, value)
        
        # Add to user index
        self.client.sadd("users", user.user_id)
        
        # Add email index for quick lookups
        self.client.set(f"email:{user.email}", user.user_id)
        
        return user
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get a user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User object or None if not found
        """
        user_key = f"user:{user_id}"
        user_data = self.client.hgetall(user_key)
        
        if not user_data:
            return None
        
        # Parse JSON fields
        for key, value in user_data.items():
            if key in ['preferences']:
                try:
                    user_data[key] = json.loads(value)
                except json.JSONDecodeError:
                    pass
            elif key == 'created_at' and value:
                try:
                    user_data[key] = datetime.fromisoformat(value)
                except ValueError:
                    user_data[key] = None
        
        return User(**user_data)
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email.
        
        Args:
            email: User email
            
        Returns:
            User object or None if not found
        """
        user_id = self.client.get(f"email:{email}")
        if user_id:
            return self.get_user(user_id)
        return None
    
    def get_all_users(self) -> List[User]:
        """Get all users from Redis.
        
        Returns:
            List of User objects
        """
        user_ids = self.client.smembers("users")
        users = []
        
        for user_id in user_ids:
            user_key = f"user:{user_id}"
            user_data = self.client.hgetall(user_key)
            
            if user_data:
                # Parse JSON fields
                for key, value in user_data.items():
                    if key in ['preferences']:
                        try:
                            user_data[key] = json.loads(value)
                        except json.JSONDecodeError:
                            pass
                    elif key == 'created_at' and value:
                        try:
                            user_data[key] = datetime.fromisoformat(value)
                        except ValueError:
                            user_data[key] = None
                
                users.append(User(**user_data))
        
        return users
    
    # Event operations
    def save_event(self, event: CalendarEvent) -> CalendarEvent:
        """Save an event to Redis.
        
        Args:
            event: CalendarEvent object to save
            
        Returns:
            CalendarEvent object with generated ID
        """
        if not event.event_id:
            event.event_id = self._generate_id("event_")
        
        if not event.created_at:
            event.created_at = datetime.now()
        
        # Store event data
        event_key = f"event:{event.event_id}"
        event_data = event.dict()
        
        # Prepare data for Redis (filter out None values and convert properly)
        redis_data = {}
        for key, value in event_data.items():
            if value is not None:  # Skip None values
                if isinstance(value, datetime):
                    redis_data[key] = value.isoformat()
                elif isinstance(value, list):
                    redis_data[key] = json.dumps(value)
                else:
                    redis_data[key] = str(value)
        
        if redis_data:  # Only call hset if we have data
            # Redis 3.x compatible version (no mapping parameter)
            for field, value in redis_data.items():
                self.client.hset(event_key, field, value)
        
        # Add to event index
        self.client.sadd("events", event.event_id)
        
        # Add to user's events
        self.client.sadd(f"user_events:{event.user_id}", event.event_id)
        
        return event
    
    def get_event(self, event_id: str) -> Optional[CalendarEvent]:
        """Get an event by ID.
        
        Args:
            event_id: Event ID
            
        Returns:
            CalendarEvent object or None if not found
        """
        event_key = f"event:{event_id}"
        event_data = self.client.hgetall(event_key)
        
        if not event_data:
            return None
        
        # Parse fields
        for key, value in event_data.items():
            if key in ['start_time', 'end_time', 'created_at'] and value:
                try:
                    event_data[key] = datetime.fromisoformat(value)
                except ValueError:
                    event_data[key] = None
            elif key == 'attendees' and value:
                try:
                    event_data[key] = json.loads(value)
                except json.JSONDecodeError:
                    event_data[key] = []
        
        return CalendarEvent(**event_data)
    
    def get_user_events(self, user_id: str) -> List[CalendarEvent]:
        """Get all events for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of CalendarEvent objects
        """
        event_ids = self.client.smembers(f"user_events:{user_id}")
        events = []
        
        for event_id in event_ids:
            event = self.get_event(event_id)
            if event:
                events.append(event)
        
        return events
    
    def get_all_events(self) -> List[CalendarEvent]:
        """Get all events from Redis.
        
        Returns:
            List of CalendarEvent objects
        """
        event_ids = self.client.smembers("events")
        events = []
        
        for event_id in event_ids:
            event_key = f"event:{event_id}"
            event_data = self.client.hgetall(event_key)
            
            if event_data:
                # Parse fields
                for key, value in event_data.items():
                    if key in ['start_time', 'end_time', 'created_at'] and value:
                        try:
                            event_data[key] = datetime.fromisoformat(value)
                        except ValueError:
                            event_data[key] = None
                    elif key == 'attendees' and value:
                        try:
                            event_data[key] = json.loads(value)
                        except json.JSONDecodeError:
                            event_data[key] = []
                
                events.append(CalendarEvent(**event_data))
        
        return events
    
    # Batch operations
    def save_batch(self, batch: GenerationBatch) -> GenerationBatch:
        """Save a generation batch to Redis.
        
        Args:
            batch: GenerationBatch object to save
            
        Returns:
            Saved GenerationBatch object
        """
        # Save users and events first
        for user in batch.users:
            self.save_user(user)
        
        for event in batch.events:
            self.save_event(event)
        
        # Save batch metadata
        batch_key = f"batch:{batch.batch_id}"
        batch_data = {
            'batch_id': batch.batch_id,
            'user_count': len(batch.users),
            'event_count': len(batch.events),
            'user_ids': json.dumps([u.user_id for u in batch.users]),
            'event_ids': json.dumps([e.event_id for e in batch.events]),
            'stats': json.dumps(batch.stats.dict()),
            'provider_used': batch.provider_used,
            'created_at': batch.created_at.isoformat()
        }
        
        # Redis 3.x compatible version (no mapping parameter)
        for field, value in batch_data.items():
            self.client.hset(batch_key, field, value)
        self.client.sadd("batches", batch.batch_id)
        
        return batch
    
    # Statistics and cleanup
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics.
        
        Returns:
            Dictionary with database statistics
        """
        return {
            'users_count': self.client.scard("users"),
            'events_count': self.client.scard("events"),
            'batches_count': self.client.scard("batches"),
            'memory_usage': self.client.info('memory')['used_memory_human'],
            'connection_status': 'connected' if self.client.ping() else 'disconnected'
        }
    
    def clear_all_data(self) -> bool:
        """Clear all calendar data from Redis.
        
        Returns:
            True if successful
        """
        try:
            # Clear main data
            keys_pattern = ["user:*", "event:*", "user_events:*", "users", "events"]
            for pattern in keys_pattern:
                for key in self.client.scan_iter(match=pattern):
                    self.client.delete(key)
            
            print(" Cleared all data from Redis")
            return True
            
        except Exception as e:
            print(f" Error clearing Redis data: {e}")
            return False 