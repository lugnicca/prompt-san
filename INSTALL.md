# PromptSan Installation Guide

## Quick Installation

### Option 1: Direct Usage (Recommended for development)

```bash
# Clone the repository
git clone https://github.com/lugnicca/prompt-san.git
cd prompt-san

# Install dependencies (Python 3.10+)
python -m pip install -r requirements.txt

# Test the installation
python - <<'PY'
from promptsan import PromptSanitizer; print('PromptSan works!')
PY
```

### Option 2: Development Installation

```bash
# Clone and install in development mode
git clone https://github.com/lugnicca/prompt-san.git
cd prompt-san
python -m pip install -e .
```

### Option 3: From PyPI (when published)

```bash
pip install promptsan
```

## Testing the Installation

### Basic Test
```bash
python - <<'PY'
from promptsan import PromptSanitizer
sanitizer = PromptSanitizer()
result = sanitizer.anonymize('Contact lugnicca@gmail.com for details')
print('Anonymized:', result.text)
print('Mapping:', result.mapping)
PY
```

### CLI Test
```bash
python -m promptsan.cli anonymize --text "Lugnicca at lugnicca@gmail.com"
```

### Run Examples
```bash
python examples/example_basic_usage.py
python examples/example_advanced_strategies.py
python examples/example_complete.py
```

## 📋 Requirements

- Python 3.10+
- Dependencies (automatically installed):
  - pydantic >= 2.0.0
  - langchain >= 0.1.0 (for LLM strategy)
  - langchain-openai >= 0.0.5 (for LLM strategy)
  - openai >= 1.0.0 (for LLM strategy)

## LLM Setup (Optional)

For LLM-based anonymization, you need a local LLM server:

### Using LM Studio
1. Download [LM Studio](https://lmstudio.ai/)
2. Download a model (e.g., dolphin-llama3.1-8b)
3. Start the server on `localhost:1234` (default port)

### Using Ollama
```bash
# Install ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Download a model
ollama pull dolphin-llama3:latest

# Start the server
ollama serve
```

## Configuration

### Basic Configuration
```python
from promptsan import SanConfig

config = SanConfig(
    strategies=["regex"],
    regex_patterns={
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b': 'EMAIL',
        r'\b\d{3}-\d{2}-\d{4}\b': 'SSN'
    }
)
```

### JSON Configuration
```json
{
 "strategies": ["regex", "dict"],
 "custom_dict": {
   "CONFIDENTIAL": "CLASSIFICATION",
   "Project Alpha": "PROJECT"
 },
 "regex_patterns": {
   "\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b": "EMAIL"
 }
}
```

## Troubleshooting

### Import Error
```bash
# Make sure you're in the right directory
cd prompt-san
python - <<'PY'
import sys; sys.path.insert(0, '.')
from promptsan import PromptSanitizer
print('OK')
PY
```

### LLM Connection Error
```bash
# Check if LLM server is running
curl http://localhost:1234/v1/models

# Or use a different port
python - <<'PY'
from promptsan import SanConfig
cfg = SanConfig(llm_base_url="http://localhost:8080/v1")
print(cfg.llm_base_url)
PY
```

### Permission Error (Windows)
```bash
# Run as administrator or use --user flag
python -m pip install --user -r requirements.txt
```

## Verification

Run this comprehensive test:

```python
from promptsan import PromptSanitizer, SanConfig

# Test 1: Basic Regex
print("Test 1: Basic Regex")
sanitizer = PromptSanitizer()
result = sanitizer.anonymize("Email john@test.com, ZIP 90210")
print(f"Result: {result.text}")
assert "__EMAIL_" in result.text and "__ZIP_" in result.text
print("Basic test passed!")

# Test 2: Dictionary Strategy
print("\nTest 2: Dictionary Strategy")
config = SanConfig(
    strategies=["dict"],
    custom_dict={"SECRET": "CLASSIFICATION"}
)
sanitizer = PromptSanitizer(config)
result = sanitizer.anonymize("This is SECRET information")
print(f"Result: {result.text}")
assert "__CLASSIFICATION_" in result.text
print("Dictionary test passed!")

# Test 3: Configuration from file
print("\nTest 3: Configuration File")
import json
with open("examples/config_basic.json", "r") as f:
    config_data = json.load(f)
config = SanConfig(**config_data)
sanitizer = PromptSanitizer(config)
result = sanitizer.anonymize("Contact admin@company.com")
print(f"Result: {result.text}")
print("Configuration file test passed!")

print("\nAll tests passed! PromptSan is ready to use!")
```

## Support

- [GitHub Issues](https://github.com/lugnicca/prompt-san/issues)
- [Documentation](https://github.com/lugnicca/prompt-san#readme)
- [Examples](./examples/)

## Next Steps

1. Run `python examples/example_complete.py` for a full feature tour
2. Check out `examples/` directory for more use cases
3. Create your own configuration files
4. Set up LLM integration for advanced anonymization

Happy anonymizing!