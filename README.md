# Calendar Management Data Generator

An open-source tool for generating realistic calendar users and events using Large Language Models (OpenAI GPT and DeepSeek). Data is stored in Redis and exported to files for further analysis or application development.

## Features

- **LLM-Powered Generation**: Uses OpenAI GPT and DeepSeek APIs to generate realistic user profiles and calendar events
- **Flexible Configuration**: YAML-based configuration for prompts, API settings, and generation parameters
- **Redis Storage**: Stores generated data in Redis for fast access and querying
- **Multiple Export Formats**: Export data to JSON and CSV files
- **CLI Interface**: Easy-to-use command-line interface with progress tracking
- **Data Validation**: Pydantic models ensure data integrity and type safety

##  Project Structure

```
CalendarManagement/
├── config/
│   └── config.yaml          # Main configuration file
├── src/
│   ├── __init__.py
│   ├── config_loader.py     # Configuration management
│   ├── llm_clients.py       # LLM API clients
│   ├── data_models.py       # Pydantic data models
│   ├── data_generator.py    # Core data generation logic
│   ├── database.py          # Redis database manager
│   └── main.py              # CLI application entry point
├── data/
│   ├── generated/           # Generated data files
│   └── exported/            # Exported data files
├── requirements.txt         # Python dependencies
├── env.example              # Environment variables template
└── README.md
```

##  Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install and Start Redis

**On Windows (using Chocolatey):**
```bash
choco install redis-64
redis-server
``` 
For me to start the redis server:(Download the open source zip file for redis and save it on your computer, then use a similar command to boot redis) 
cd "C:\Users\himni\OneDrive\Documents\Redis-x64-3.0.504" 
 .\redis-server.exe
```

**On macOS (using Homebrew):**
```bash
brew install redis
brew services start redis
```

**On Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis
```

### 3. Configure API Keys

1. Copy the environment template:
   ```bash
   cp env.example .env
   ```

2. Edit `.env` and add your API keys:
   ```bash
   OPENAI_API_KEY=your_openai_api_key_here
   DEEPSEEK_API_KEY=your_deepseek_api_key_here
   ```

### 4. Customize Configuration (Optional)

Edit `config/config.yaml` to customize:
- Number of users and events to generate
- LLM prompts for user and event generation
- API settings (models, temperature, etc.)
- Output formats and directories

##  Usage

### Basic Commands

**Test connections:**
```bash
python -m src.main test-connection
```

**Generate data with default settings:**
```bash
python -m src.main generate
```

**Generate specific number of users:**
```bash
python -m src.main generate --users 5
```

**Use specific LLM provider:**
```bash
python -m src.main generate --provider openai
python -m src.main generate --provider deepseek
```

**View database statistics:**
```bash
python -m src.main stats
```

**Export existing data:**
```bash
python -m src.main export --format json
python -m src.main export --format csv
```

**Clear all data:**
```bash
python -m src.main clear
```

### Advanced Usage

**Dry run (see what would be generated):**
```bash
python -m src.main generate --dry-run --users 50
```

**Generate with specific provider and custom count:**
```bash
python -m src.main generate --users 25 --provider deepseek
```

##  Tools and Frameworks Used

### Core Dependencies
- **PyYAML**: YAML configuration file handling
- **Pydantic**: Data validation and serialization
- **Click**: Command-line interface framework
- **python-dotenv**: Environment variable management

### LLM Integration
- **OpenAI**: Official OpenAI Python client
- **Requests**: HTTP client for DeepSeek API

### Database & Storage
- **Redis**: In-memory data structure store

### Data Processing
- **Pandas**: Data manipulation and CSV export
- **Faker**: Realistic fake data generation (backup)

##  Generated Data Structure

### User Profile
```json
{
  "user_id": "user_abc12345",
  "name": "John Doe",
  "email": "john.doe@example.com",
  "timezone": "America/New_York",
  "profession": "Software Engineer",
  "preferences": {
    "working_hours": {
      "start": "09:00",
      "end": "17:00"
    },
    "meeting_duration_preference": "30-60 minutes",
    "calendar_view": "week"
  },
  "created_at": "2024-01-15T10:30:00"
}
```

### Calendar Event
```json
{
  "event_id": "event_def67890",
  "user_id": "user_abc12345",
  "title": "Team Standup",
  "description": "Daily team synchronization meeting",
  "start_time": "2024-01-16T10:00:00",
  "end_time": "2024-01-16T10:30:00",
  "location": "Virtual",
  "attendees": ["team@company.com"],
  "category": "meeting",
  "priority": "medium",
  "recurrence": null,
  "created_at": "2024-01-15T10:30:00"
}
```

##  Configuration Options

The `config/config.yaml` file allows you to customize:

- **API Settings**: Model names, temperature, max tokens
- **Generation Counts**: Number of users and events per user
- **Prompts**: Custom prompts for user and event generation
- **Output Settings**: Export formats and directories
- **Database Settings**: Redis connection parameters

##  Example Workflows

### 1. Quick Start
```bash
# Test everything works
python -m src.main test-connection

# Generate sample data
python -m src.main generate --users 10

# Check what was created
python -m src.main stats
```

### 2. Large Dataset Generation
```bash
# Generate large dataset using OpenAI
python -m src.main generate --users 500 --provider openai

# Export to CSV for analysis
python -m src.main export --format csv

# Clear when done
python -m src.main clear
```

### 3. Research/Development Workflow
```bash
# Generate small test dataset
python -m src.main generate --users 20

# Export to JSON for development
python -m src.main export --format json

# Check Redis directly if needed
redis-cli
> KEYS *
> HGETALL user:user_abc12345
```

##  Contributing

This is an open-source educational project. Feel free to:

1. Fork the repository
2. Create feature branches
3. Submit pull requests
4. Report issues or suggest improvements

##  License

This project is open source and available under the MIT License.

##  Troubleshooting

**Redis Connection Issues:**
- Ensure Redis server is running: `redis-cli ping`
- Check Redis configuration in `config/config.yaml`

**API Key Issues:**
- Verify API keys are set in `.env` file
- Test individual APIs with `test-connection` command

**Generation Failures:**
- Check API quotas and rate limits
- Reduce batch sizes in configuration
- Try different LLM providers

##  Learning Resources

- [OpenAI API Documentation](https://platform.openai.com/docs)
- [DeepSeek API Documentation](https://api.deepseek.com/docs)
- [Redis Documentation](https://redis.io/documentation)
- [Pydantic Documentation](https://docs.pydantic.dev)
- [Click Documentation](https://click.palletsprojects.com) 