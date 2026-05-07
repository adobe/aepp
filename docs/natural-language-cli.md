# Natural Language CLI Interface

The Adobe AEP CLI now supports natural language commands using OpenAI-compatible APIs.

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install the `openai` package along with other dependencies.

### 2. Configure Environment Variables

Set the following environment variables:

```bash
# Required: Your OpenAI API key
export OPENAI_API_KEY="sk-..."

# Optional: Custom endpoint for OpenAI-compatible APIs (e.g., Azure OpenAI, local models)
export OPENAI_API_ENDPOINT="https://api.openai.com/v1"

# Optional: Model to use (defaults to gpt-4)
export OPENAI_MODEL="gpt-4"
```

### For Azure OpenAI

```bash
export OPENAI_API_KEY="your-azure-key"
export OPENAI_API_ENDPOINT="https://your-resource.openai.azure.com/openai/deployments/your-deployment"
export OPENAI_MODEL="gpt-4"
```

### For Local Models (e.g., LM Studio, Ollama with OpenAI compatibility)

```bash
export OPENAI_API_KEY="not-needed"
export OPENAI_API_ENDPOINT="http://localhost:1234/v1"
export OPENAI_MODEL="local-model"
```

## Usage

### Start the CLI

```bash
python -m aepp.cli -cf config.json
```

If the OpenAI client is properly configured, you'll see:
```
Natural language mode enabled
```

### Using the `ask` Command

Instead of remembering exact command names and parameters, you can now ask in natural language:

```bash
prod> ask show me all schemas
```

This will automatically translate to and execute: `get_schemas`

### More Examples

```bash
# List all datasets
prod> ask list all datasets

# Get schema information
prod> ask get details for MySchema

# Show audiences
prod> ask what audiences do we have?

# List sandboxes
prod> ask show me all sandboxes

# Get identities
prod> ask show me the identities

# List flows with details
prod> ask show me the flows
```

## How It Works

1. You type: `ask <your natural language request>`
2. The CLI sends your request along with all available commands to the OpenAI API
3. The AI translates your request to the appropriate CLI command
4. The command is executed automatically

## Troubleshooting

### "Natural language mode requires the 'openai' package"

Install the package:
```bash
pip install openai
```

### "Natural language mode is not enabled"

Set the `OPENAI_API_KEY` environment variable:
```bash
export OPENAI_API_KEY="sk-..."
```

### "OpenAI API error"

Check that:
- Your API key is valid
- Your endpoint URL is correct (if using a custom endpoint)
- You have internet connectivity
- Your API has sufficient credits/quota

## Traditional Commands Still Work

All traditional commands continue to work as before:

```bash
prod> get_schemas
prod> get_datasets
prod> get_audiences
```

The `ask` command is an additional convenience feature that doesn't replace the existing functionality.
