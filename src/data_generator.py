"""
Data generator for creating users and calendar events using LLMs.

This module orchestrates the entire data generation process:
1. Initialize LLM clients based on available API keys
2. Generate realistic users using LLM prompts
3. Generate events for each user based on their profile
4. Save everything to Redis and export to files

Architecture Pattern: Service Layer / Orchestrator
- Combines multiple components (LLM clients, database, config)
- Handles the business logic of data generation
- Manages error handling and statistics
- Coordinates between different layers

Why LLMs for data generation?
- More realistic than random generation
- Context-aware (events match user profiles)
- Customizable through prompts
- Diverse output (each generation is unique)
"""

import json
import random
from datetime import datetime
from typing import List, Dict, Any, Tuple
import uuid

from .config_loader import ConfigLoader
from .llm_clients import LLMClientFactory, LLMClient
from .data_models import User, CalendarEvent, GenerationStats
from .database import RedisManager


class DataGenerator:
    """Generates realistic calendar data using LLMs."""
    
    def __init__(self, config_loader: ConfigLoader, redis_manager: RedisManager):
        """Initialize the data generator.
        
        Args:
            config_loader: Configuration loader instance
            redis_manager: Redis database manager
        """
        self.config = config_loader #This is the config loader, it is used to load the config from the config.json file
        self.redis = redis_manager #This is the redis database manager, it is used to save the data to the database
        self.stats = GenerationStats() #This is the generation stats, it is used to track the generation stats
        
        # Initialize LLM clients
        self.clients = {}
        for provider in ['openai', 'deepseek']: #This is the list of providers that are available, it is used to create the clients
            try:
                api_config = self.config.get_api_config(provider)
                if api_config.get('api_key'):
                    self.clients[provider] = LLMClientFactory.create_client(provider, api_config) #This is the client factory, it is used to create the clients
                    print(f" Initialized {provider} client")
                else:
                    print(f" No API key found for {provider}")
            except Exception as e:
                print(f" Failed to initialize {provider} client: {e}")
        
        if not self.clients:
            raise ValueError("No LLM clients available. Please check your API keys.")
    
    def _get_client(self, preferred_provider: str = None) -> Tuple[str, LLMClient]:
        """Get an available LLM client.
        
        Args:
            preferred_provider: Preferred provider name
            
        Returns:
            Tuple of (provider_name, client)
        """
        if preferred_provider and preferred_provider in self.clients:
            return preferred_provider, self.clients[preferred_provider] #.client creates the client object, here client is an entity that uses the api key to generate the text
        
        # Return first available client
        provider = list(self.clients.keys())[0]
        return provider, self.clients[provider]
    
    def generate_users(self, count: int, provider: str = None) -> List[User]:
        """Generate realistic users using LLM.
        
        Args:
            count: Number of users to generate
            provider: Preferred LLM provider
            
        Returns:
            List of generated User objects
        """
        print(f" Generating {count} users...")
        
        provider_name, client = self._get_client(provider)
        prompt = self.config.get_prompts().get('user_generation', '') #This is the prompt that is used to generate the users
        
        if not prompt:
            raise ValueError("User generation prompt not found in config")
        
        users = []
        
        # Try to generate users one by one for better reliability with uniqueness
        for i in range(count):
            try:
                # Build list of already generated names to avoid duplicates
                existing_names = [user.name for user in users]
                existing_emails = [user.email for user in users]
                
                if existing_names:
                    uniqueness_instruction = f"\n\nIMPORTANT: Do NOT use these already generated names: {', '.join(existing_names)}\nDo NOT use these emails: {', '.join(existing_emails)}\nGenerate a completely different person with a unique name and email."
                else:
                    uniqueness_instruction = "\n\nGenerate a unique person with realistic name and email."
                
                user_prompt = f"Generate 1 realistic user profile. Return a JSON array with exactly 1 user:\n\n{prompt}{uniqueness_instruction}"
                response = client.generate_text(user_prompt)
                self.stats.total_api_calls += 1
                
                print(f" Generating user {i+1}/{count}...")
                
                parsed_data = client._parse_json_response(response) #This is the function that is used to parse the response from the client
                if isinstance(parsed_data, dict): #This is the condition that is used to check if the response is a dictionary
                    parsed_data = [parsed_data]
                
                if parsed_data and len(parsed_data) > 0:
                    data = parsed_data[0]  # Take the first user #This is the data that is used to create the user
                    try:
                        user = User(**data)
                        user.user_id = f"user_{uuid.uuid4().hex[:8]}" #This is the user id that is used to identify the user
                        user.created_at = datetime.now() #This is the date and time when the user was created
                        users.append(user) #This is the list of users that are created
                        self.stats.users_generated += 1
                        print(f" Created user: {user.name}") #This is the message that is printed when the user is created
                    except Exception as e:
                        print(f" Failed to create user: {e}") #This is the message that is printed when the user is not created
                        self.stats.failed_generations += 1 #This is the counter that is used to track the number of failed generations
                else:
                    print(f" No user data returned for user {i+1}") #This is the message that is printed when the user is not created
                    self.stats.failed_generations += 1 #This is the counter that is used to track the number of failed generations
                
            except Exception as e:
                print(f" Failed to generate user {i+1}: {e}")
                self.stats.failed_generations += 1
        
        print(f" Generated {len(users)} users using {provider_name}")
        return users
    
    def generate_events_for_user(self, user: User, count: int = None, provider: str = None) -> List[CalendarEvent]:
        """Generate events for a specific user.
        
        Args:
            user: User object to generate events for
            count: Number of events to generate (random if None)
            provider: Preferred LLM provider
            
        Returns:
            List of generated CalendarEvent objects
        """
        if count is None:
            count = random.randint(2, 4)  # Reduced to be more reliable #This is the number of events that are generated for each user
        
        provider_name, client = self._get_client(provider)
        prompt_template = self.config.get_prompts().get('event_generation', '') #This is the prompt that is used to generate the events
        
        if not prompt_template:
            raise ValueError("Event generation prompt not found in config") #This is the error message that is printed when the prompt is not found
        
        # Format prompt with user data
        prompt = prompt_template.format(
            count=count, #This is the number of events that are generated for each user
            user_name=user.name, #This is the name of the user
            profession=user.profession, #This is the profession of the user
            timezone=user.timezone, #This is the timezone of the user
            working_hours=f"{user.preferences.working_hours.start} - {user.preferences.working_hours.end}" #This is the working hours of the user
        )
        
        # Try with retries and fallback to smaller batches
        max_retries = 2
        for attempt in range(max_retries):
            try:
                response = client.generate_text(prompt, max_retries=2)
                self.stats.total_api_calls += 1
                
                print(f" Raw response for {user.name}: {response[:100]}...")
                
                parsed_data = client._parse_json_response(response) #This is the function that is used to parse the response from the client
                if not isinstance(parsed_data, list): #This is the condition that is used to check if the response is a list
                    if isinstance(parsed_data, dict): #This is the condition that is used to check if the response is a dictionary
                        parsed_data = [parsed_data]  # Single event case
                    else:
                        raise ValueError("Expected array of events") #This is the error message that is printed when the response is not a list
                
                events = [] #This is the list of events that are created
                for event_data in parsed_data: #This is the loop that is used to create the events
                    try:
                        event_data['user_id'] = user.user_id #This is the user id that is used to identify the user
                        event_data['event_id'] = f"event_{uuid.uuid4().hex[:8]}" #This is the event id that is used to identify the event
                        event_data['created_at'] = datetime.now() #This is the date and time when the event was created
                        
                        # Parse datetime strings more robustly
                        for time_field in ['start_time', 'end_time']: #This is the list of time fields that are used to parse the datetime strings
                            if time_field in event_data and isinstance(event_data[time_field], str): #This is the condition that is used to check if the time field is a string
                                time_str = event_data[time_field].replace('Z', '+00:00') #This is the function that is used to replace the Z with +00:00
                                if 'T' not in time_str:
                                    time_str = f"2024-12-26T{time_str}"
                                event_data[time_field] = datetime.fromisoformat(time_str)
                        
                        event = CalendarEvent(**event_data)
                        events.append(event)
                        self.stats.events_generated += 1
                        
                    except Exception as e:
                        print(f" Failed to create event: {e}")
                        self.stats.failed_generations += 1
                
                if events:  # Success if we got at least one event
                    return events
                    
            except Exception as e:
                print(f" Attempt {attempt + 1} failed for {user.name}: {str(e)[:100]}")
                if attempt < max_retries - 1:
                    # Try again with simpler request
                    count = min(count, 2)
                    continue
                else:
                    self.stats.failed_generations += count
                    print(f" All attempts failed for {user.name}")
                    return []
        
        return []
    
    def generate_and_save(self, user_count: int = None, provider: str = None) -> Dict[str, Any]:
        """Generate complete dataset and save to Redis and files."""
        self.stats.start_time = datetime.now()
        
        try:
            if user_count is None:
                user_count = self.config.get_generation_config().get('users', {}).get('count', 50)
            
            # Generate users
            users = self.generate_users(user_count, provider)
            
            if not users:
                raise ValueError("No users were successfully generated")
            
            # Generate events
            all_events = []
            for user in users:
                events = self.generate_events_for_user(user, provider=provider)
                all_events.extend(events)
            
            # Save to Redis
            for user in users:
                self.redis.save_user(user)
            for event in all_events:
                self.redis.save_event(event)
            
            # Export to files
            file_paths = self._export_to_files(users, all_events)
            
            self.stats.end_time = datetime.now()
            
            return {
                'users_generated': len(users),
                'events_generated': len(all_events),
                'duration_seconds': self.stats.duration_seconds,
                'api_calls': self.stats.total_api_calls,
                'failed_generations': self.stats.failed_generations,
                'exported_files': file_paths
            }
            
        except Exception as e:
            self.stats.end_time = datetime.now()
            # Re-raise with more context
            raise Exception(f"Data generation failed: {str(e)[:200]}")  # Limit error message length
    
    def _export_to_files(self, users: List[User], events: List[CalendarEvent]) -> Dict[str, str]:
        """Export data to JSON files."""
        from pathlib import Path
        
        output_dir = Path("data/generated")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Export users
        users_file = output_dir / f"users_{timestamp}.json"
        with open(users_file, 'w', encoding='utf-8') as f:
            json.dump([user.dict() for user in users], f, indent=2, default=str)
        
        # Export events
        events_file = output_dir / f"events_{timestamp}.json"
        with open(events_file, 'w', encoding='utf-8') as f:
            json.dump([event.dict() for event in events], f, indent=2, default=str)
        
        return {
            'users_file': str(users_file),
            'events_file': str(events_file)
        } 