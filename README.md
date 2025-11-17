# AIDiveLog - AI-Powered Dive Log Assistant

An intelligent dive log management system that uses AI to help you search, query, and manage your dive logs. The system uses Pinecone for semantic search and OpenAI GPT-4 for natural language interactions.

## Features

- **Semantic Search**: Search your dive logs using natural language queries
- **Interactive Q&A**: Ask questions about your dive history in plain English
- **Dive Log Creation**: Add new dive entries through conversational interface
- **RAG System**: Retrieval-Augmented Generation for context-aware responses
- **Pinecone Integration**: Uses Pinecone with integrated embeddings for efficient search

## Prerequisites

- Python 3.12 or higher
- Poetry (for dependency management)
- Pinecone API key ([Get one here](https://www.pinecone.io/))
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
- `pinecone` (>=7.3.0,<8.0.0)
- `pyautogen` (>=0.2.0)
- `autogen-ext[openai]` (>=0.7.0)
- `openai` (>=1.0.0)
- `python-dotenv` (>=1.0.0)

## Configuration

### 1. Set Up Environment Variables

Create a `.env` file in the project root directory:

```bash
PINECONE_API_KEY=your-pinecone-api-key-here
OPENAI_API_KEY=your-openai-api-key-here
```

Alternatively, you can export them in your shell:

```bash
export PINECONE_API_KEY="your-pinecone-api-key"
export OPENAI_API_KEY="your-openai-api-key"
```

### 2. Initialize Pinecone Index and Populate Sample Data

Before running the assistant, you need to create the Pinecone index and populate it with dive log data:

```bash
poetry run python populate_dive_log.py
```

This script will:
- Create a Pinecone index named `aidivelog-index` (if it doesn't exist)
- Populate it with 30 sample dive log records
- Test the search functionality
- Display index statistics

**Note**: The first time you run this, it may take a few minutes to create the index and index the vectors. The script will wait for indexing to complete.

## Running the Application

### Start the Dive Log Assistant

Once the index is set up, run the interactive assistant:

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

2. **Get aggregated information**: Ask questions that require analyzing multiple dives:
   - "How many wreck dives have I done?"
   - "What's my deepest dive?"
   - "Where did I dive most frequently?"

3. **Add new dive logs**: Describe a dive and the assistant will create an entry:
   - "I did a dive today at Blue Corner in Palau. It was a 45-minute recreational dive to 30 meters. We saw barracuda schools and reef sharks."

4. **Exit**: Type `quit`, `exit`, `bye`, or `goodbye` to end the conversation

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
│   ├── agents.py              # AutoGen agent definitions
│   ├── dive_log_assistant.py  # Main application entry point
│   ├── pinecone_service.py    # Pinecone RAG service
│   └── tools.py               # Agent tools (search_dive_logs, create_dive_log)
├── populate_dive_log.py       # Script to initialize index and populate sample data
├── pyproject.toml             # Poetry dependencies and project configuration
├── poetry.lock                # Locked dependency versions
└── README.md                  # This file
```

## How It Works

1. **Pinecone Vector Database**: Dive logs are stored in Pinecone with integrated embeddings using the `llama-text-embed-v2` model. Each dive log includes metadata (location, depth, dive type, etc.) and content (narrative description).

2. **Semantic Search**: When you ask a question, the system:
   - Converts your query into an embedding
   - Searches the Pinecone index for similar dive logs
   - Optionally uses reranking (`bge-reranker-v2-m3`) for better relevance
   - Applies metadata filters (location, dive type, depth) when specified

3. **AI Agent**: The AutoGen assistant agent:
   - Understands your natural language queries
   - Calls the appropriate tools (`search_dive_logs` or `create_dive_log`)
   - Synthesizes results into natural language responses
   - Only returns information from your actual dive logs (no hallucinations)

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

### Changing the Pinecone Index

Edit `aidivelog/pinecone_service.py` to change the index name or namespace:

```python
def __init__(self, index_name: str = "aidivelog-index", namespace: str = "dive-logs"):
```

## Troubleshooting

### Index Not Found Error

If you see an error about the index not existing:
1. Run `populate_dive_log.py` to create and populate the index
2. Wait a few seconds after running the script for indexing to complete

### API Key Errors

Verify your API keys are set correctly:

```bash
# Check if environment variables are set
echo $PINECONE_API_KEY
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

## Adding Your Own Dive Logs

To add your own dive logs, you can either:

1. **Use the assistant**: Simply describe your dive in natural language and the assistant will create the entry
2. **Modify the populate script**: Edit the `records` list in `populate_dive_log.py` and run it again (it will upsert new records)

## Development

### Running Tests

The `populate_dive_log.py` script includes search tests that verify the system is working correctly.

### Extending Functionality

- **New Tools**: Add functions to `tools.py` and register them in `agents.py`
- **Custom Filters**: Modify `pinecone_service.py` to add new search capabilities
- **Agent Behavior**: Adjust the system message in `agents.py` to change how the assistant behaves

## License

[Add your license here]
