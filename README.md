# AIDiveLog - AI-Powered Dive Log Assistant

An intelligent dive log management system that uses AI to help you search, query, and manage your dive logs. Built with AutoGen agents, OpenAI GPT-4, and SQLite with full-text search capabilities.

## Features

- **Full-Text Search**: Search your dive logs using natural language queries powered by SQLite FTS5
- **Interactive Q&A**: Ask questions about your dive history in plain English
- **Dive Log Creation**: Add new dive entries through conversational interface
- **Persistent Memory**: The assistant remembers your name and preferred units (metric/imperial) across conversations
- **Metadata Filtering**: Filter searches by location, dive type, and depth
- **AutoGen Agents**: Uses Microsoft AutoGen framework for intelligent agent-based interactions

## Prerequisites

- Python 3.12 or higher
- Poetry (for dependency management)
- OpenAI API key ([Get one here](https://platform.openai.com/))

## Installation

### 1. Install Poetry (if not already installed)

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### 2. Install Project Dependencies

```bash
poetry install
```

This will install all required dependencies including:
- `pyautogen` (>=0.2.0) - AutoGen framework for agent-based AI
- `autogen-ext[ui]` (>=0.7.5,<0.8.0) - AutoGen extensions with UI support
- `openai` (>=1.0.0) - OpenAI API client
- `python-dotenv` (>=1.0.0) - Environment variable management
- `tiktoken` (>=0.12.0,<0.13.0) - Token counting for OpenAI models

## Configuration

### 1. Set Up Environment Variables

Create a `.env` file in the project root directory:

```bash
OPENAI_API_KEY=your-openai-api-key-here
```

Alternatively, you can export it in your shell:

```bash
export OPENAI_API_KEY="your-openai-api-key"
```

### 2. Initialize Database and Populate Sample Data

Before running the assistant, you need to populate the SQLite database with dive log data:

```bash
poetry run python populate_dive_log.py
```

This script will:
- Initialize the SQLite database (`aidivelog.db`) with the required schema
- Create FTS5 (Full-Text Search) virtual tables for efficient text search
- Populate the database with sample dive log records from `sample_dives.json`
- Test the search functionality
- Display search results to verify everything is working

**Note**: The database is automatically created on first use if it doesn't exist. The `populate_dive_log.py` script is primarily for adding sample data.

## Running the Application

### Start the Dive Log Assistant

Once the database is set up, run the interactive assistant:

```bash
poetry run python -m aidivelog.dive_log_assistant
```

Or if you're already in a Poetry shell:

```bash
poetry shell
python -m aidivelog.dive_log_assistant
```

### Using the Assistant

The assistant provides an interactive command-line interface where you can:

1. **Search your dive logs**: Ask questions like:
   - "What wreck dives did I do in Thailand?"
   - "Show me all my cave dives"
   - "What dives did I do in the Red Sea?"
   - "Find dives with manta rays"
   - "Show me shallow dives under 20 meters"

2. **Get aggregated information**: Ask questions that require analyzing multiple dives:
   - "How many wreck dives have I done?"
   - "What's my deepest dive?"
   - "Where did I dive most frequently?"
   - "What's my total dive time?"

3. **Add new dive logs**: Describe a dive and the assistant will create an entry:
   - "I did a dive today at Blue Corner in Palau. It was a 45-minute recreational dive to 30 meters. We saw barracuda schools and reef sharks."
   - "Add a night dive from yesterday at 8pm on the house reef in Bonaire. It was 48 minutes, max depth 20 meters, average 15 meters. We saw octopuses and bioluminescent plankton."

4. **Set preferences**: Tell the assistant your preferences:
   - "My name is Alex"
   - "I prefer metric units" or "Use imperial units"

5. **Exit**: Type `quit`, `exit`, `bye`, or `goodbye` to end the conversation

### Example Session

```
============================================================
DIVE ASSISTANT - Dive Log Q&A
============================================================

Type 'quit' or 'exit' to end the conversation.

============================================================

Initializing assistant...
Assistant initialized!

Assistant ready! How can I help you today?

You: My name is Alex and I prefer metric units

Assistant: Nice to meet you, Alex! I've saved your name and your preference for metric units. I'll use metric units for all measurements going forward.

You: What wreck dives did I do in Egypt?

Assistant: Based on your dive logs, I found the following wreck dives in Egypt:

1. SS Thistlegorm (Red Sea, Egypt)
   - Date: 2024-04-22 at 11:00
   - Depth: 30m max, 25m average
   - Duration: 52 minutes
   - Type: wreck, recreational
   - Highlights: WWII wreck, motorcycles, trucks, glassfish, batfish, cargo holds

2. Cargo Wreck (Red Sea, Egypt)
   - Date: 2025-05-12 at 12:00
   - Depth: 25m max, 20m average
   - Duration: 45 minutes
   - Type: wreck, recreational
   - Highlights: wreck penetration, cargo holds, crew quarters, glassfish, groupers

You: Add a new dive: I did a night dive yesterday at 8pm on the house reef in Bonaire. It was 48 minutes, max depth 20 meters, average 15 meters. We saw octopuses and bioluminescent plankton.

Assistant: I've successfully created a new dive log entry for your night dive in Bonaire. The dive has been saved with ID: [uuid].

You: quit

Goodbye! Happy diving!
```

## Project Structure

```
AIDiveLog/
├── aidivelog/
│   ├── __init__.py
│   ├── agents.py              # AutoGen agent definitions and configuration
│   ├── config.py              # Configuration and environment variable loading
│   ├── dive_log_assistant.py  # Main application entry point
│   ├── sqlite_service.py      # SQLite database service with FTS5 search
│   └── tools.py               # Agent tools (search_dive_logs, create_dive_log, etc.)
├── populate_dive_log.py       # Script to populate database with sample data
├── sample_dives.json          # Sample dive log data in JSON format
├── aidivelog.db               # SQLite database (created automatically)
├── pyproject.toml             # Poetry dependencies and project configuration
├── poetry.lock                # Locked dependency versions
└── README.md                  # This file
```

## How It Works

1. **SQLite Database**: Dive logs are stored in a SQLite database with:
   - Main `dive_logs` table storing all dive information
   - FTS5 virtual table (`dive_logs_fts`) for full-text search on content, location, and highlights
   - Automatic triggers to keep FTS5 in sync with the main table
   - User preferences table for persistent memory

2. **Full-Text Search**: When you ask a question, the system:
   - Uses SQLite FTS5 to search dive log content, locations, and highlights
   - Applies BM25 ranking algorithm for relevance scoring
   - Optionally applies metadata filters (location, dive type, depth) when specified
   - Combines text search results with filtered results for comprehensive answers

3. **AI Agent**: The AutoGen assistant agent:
   - Uses OpenAI GPT-4 for natural language understanding
   - Has access to persistent memory for user preferences
   - Calls appropriate tools (`search_dive_logs`, `create_dive_log`, `get_all_dives`, etc.)
   - Synthesizes results into natural language responses
   - Only returns information from your actual dive logs (no hallucinations)

4. **Memory System**: The assistant remembers:
   - Your name (stored when you tell it)
   - Preferred units (metric or imperial)
   - Preferences persist across all conversations via SQLite

## Available Tools

The assistant has access to the following tools:

- **`search_dive_logs`**: Search dive logs by text query, location, dive type, and max depth
- **`get_all_dives`**: Retrieve all dive logs from the database (useful for aggregations)
- **`create_dive_log`**: Create a new dive log entry with required and optional fields
- **`save_user_preference`**: Save user preferences (name, units, etc.) to persistent storage
- **`get_user_preference`**: Retrieve stored user preferences

## Customization

### Changing the Model

Edit `aidivelog/agents.py` to change the OpenAI model:

```python
return OpenAIChatCompletionClient(
    model="gpt-4.1",  # Change this to "gpt-4", "gpt-3.5-turbo", etc.
    api_key=api_key,
    temperature=0.3,  # Adjust for more/less creativity
)
```

### Changing the Database Location

Edit `aidivelog/sqlite_service.py` to change the database path:

```python
def __init__(self, db_path: Optional[str] = None):
    if db_path is None:
        project_root = Path(__file__).parent.parent
        db_path = project_root / "aidivelog.db"  # Change this path
```

### Adjusting Agent Behavior

Edit the `system_message` in `aidivelog/agents.py` to change how the assistant behaves, responds, or uses tools.

## Troubleshooting

### Database Not Found Error

If you see an error about the database not existing:
1. The database is automatically created on first use
2. Run `populate_dive_log.py` to add sample data
3. Check that you have write permissions in the project directory

### API Key Errors

Verify your API key is set correctly:

```bash
# Check if environment variable is set
echo $OPENAI_API_KEY

# Or check your .env file
cat .env
```

### Import Errors

Make sure you're running with Poetry:

```bash
poetry run python -m aidivelog.dive_log_assistant
```

Or activate the Poetry shell first:

```bash
poetry shell
python -m aidivelog.dive_log_assistant
```

### Module Not Found Errors

If you get import errors, ensure you're in the project root directory and all dependencies are installed:

```bash
poetry install
```

### Search Not Returning Results

- Make sure you've populated the database with `populate_dive_log.py`
- Try broader search queries
- Check that the FTS5 index is properly initialized (it should be automatic)

## Adding Your Own Dive Logs

To add your own dive logs, you can either:

1. **Use the assistant**: Simply describe your dive in natural language and the assistant will create the entry
2. **Modify the populate script**: Edit `sample_dives.json` and run `populate_dive_log.py` again (it will insert new records)
3. **Direct database access**: Use the `SQLiteService` class programmatically to add dives

## Database Schema

The SQLite database contains:

- **`dive_logs`**: Main table with columns:
  - `id` (TEXT, PRIMARY KEY): UUID for each dive
  - `content` (TEXT): Narrative description of the dive
  - `location_site` (TEXT): Name of the dive site
  - `location_area` (TEXT): Area or region
  - `location_country` (TEXT): Country
  - `depth_max` (INTEGER): Maximum depth in meters
  - `depth_avg` (INTEGER): Average depth in meters
  - `length_minutes` (INTEGER): Dive duration in minutes
  - `dive_type` (TEXT): Type of dive (recreational, wreck, cave, decompression)
  - `highlights` (TEXT): Notable features or highlights
  - `date` (TEXT): Dive date (YYYY-MM-DD)
  - `time` (TEXT): Dive time (HH:MM)
  - `equipment_used` (TEXT): JSON array of equipment

- **`dive_logs_fts`**: FTS5 virtual table for full-text search
- **`user_preferences`**: Table for storing user preferences (name, units, etc.)

## Development

### Running Tests

The `populate_dive_log.py` script includes search tests that verify the system is working correctly.

### Extending Functionality

- **New Tools**: Add functions to `tools.py` and register them in `agents.py` as `FunctionTool` instances
- **Custom Filters**: Modify `sqlite_service.py` to add new search capabilities or filters
- **Agent Behavior**: Adjust the system message in `agents.py` to change how the assistant behaves
- **Memory**: Extend the memory system in `agents.py` to store additional user preferences

## License

[Add your license here]
