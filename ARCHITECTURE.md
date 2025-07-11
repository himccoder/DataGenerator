# Calendar Data Generator - Architecture Guide

## Overall Architecture

This project follows **Layered Architecture**:

```
┌─────────────────────────────────────────────────┐
│                CLI Layer                        │ ← User Interface (main.py)
│              (Click Framework)                  │
├─────────────────────────────────────────────────┤
│            Business Logic Layer                 │ ← Core Logic (data_generator.py)
│           (Service/Orchestrator)                │
├─────────────────────────────────────────────────┤
│             Data Access Layer                   │ ← Database Operations (database.py)
│           (Repository Pattern)                  │
├─────────────────────────────────────────────────┤
│           External Services Layer               │ ← API Integrations (llm_clients.py)
│            (Strategy Pattern)                   │
├─────────────────────────────────────────────────┤
│              Data Models Layer                  │ ← Data Structures (data_models.py)
│            (Domain Models)                      │
├─────────────────────────────────────────────────┤
│           Configuration Layer                   │ ← Settings Management (config_loader.py)
│         (Configuration as Code)                 │
└─────────────────────────────────────────────────┘
```

## File-by-File Breakdown

### 1. `config/config.yaml` - Application Configuration

```yaml
# Contains:
- LLM API settings (models, temperature, tokens)
- Generation parameters (user count, events per user)
- LLM prompts for data generation
- Database connection settings
- Export formats and directories
```


### 2. `src/config_loader.py` - Configuration Management

```python
# Process:
1. Load .env file (local development secrets/API keys)
2. Load YAML config (application settings)  
3. Override with environment variables (deployment flexibility)
```


### 3. `src/data_models.py` - Data Structures

```python
# Models defined:
- User: Represents a calendar user
- CalendarEvent: Represents a calendar event  
- UserPreferences: Nested user settings
- GenerationStats: Tracks generation metrics
```


### 4. `src/llm_clients.py` - LLM API Integration

```python
# Architecture:
LLMClient (Abstract Base) ← Interface
├── OpenAIClient ← Concrete implementation
├── DeepSeekClient ← Concrete implementation
└── LLMClientFactory ← Creates appropriate client
```


### 5. `src/database.py` - Data Persistence

```python
# Redis Data Structure:
user:{id} → Hash of user data
event:{id} → Hash of event data
users → Set of all user IDs (index)
events → Set of all event IDs (index)
user_events:{user_id} → Set of event IDs for user
```


### 6. `src/data_generator.py` - Core Business Logic

```python
# Process Flow:
1. Initialize LLM clients based on available API keys
2. Generate users using configured prompts
3. Generate events for each user (context-aware)
4. Save all data to Redis
5. Export to files
6. Track statistics
```


### 7. `src/main.py` - CLI Interface

```python
# Available Commands:
- generate: Create new data
- stats: Show database statistics
- export: Export data to files
- clear: Clear all data
- test-connection: Test API/database connections
```



##  Data Flow

### Generation Flow:
```
User Command → CLI → DataGenerator → LLM Client → API
                ↓                              ↑
            RedisManager ← Generated Data ←────┘
                ↓
          Export to Files
```

### Configuration Flow:
```
config.yaml → ConfigLoader ← .env file
     ↓              ↓
   Settings → Environment Variables
     ↓              ↓
   All Components Get Configuration
```

