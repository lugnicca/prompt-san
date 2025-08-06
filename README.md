# PromptSan

**Minimal yet powerful text anonymization library**

PromptSan is a little library for anonymizing and deanonymizing text with pluggable strategies. It supports regex patterns, custom dictionaries, LLM-based anonymization, and streaming deanonymization.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- **Multiple Strategies**: Regex, dictionary, and LLM-based anonymization
- **Streaming Support**: Real-time deanonymization for LLM outputs
- **Extensible**: Easy to add custom anonymization strategies
- **Type-Safe**: Full type hints and Pydantic validation
- **Minimal**: Only 5 core files, clean architecture
- **LLM Integration**: Local LLM support via LangChain
- **Streaming**: Generator-based streaming deanonymization

## Installation

### From PyPI (when published)
```bash
pip install promptsan
```

### From Source
```bash
git clone https://github.com/lugnicca/prompt-san.git
cd promptsan
pip install -e .
```

### Development Installation
```bash
git clone https://github.com/lugnicca/prompt-san.git
cd promptsan
pip install -e ".[dev]"
```

## Quick Start

### Basic Usage

```python
from promptsan import PromptSanitizer, SanConfig

# Default configuration (regex strategy)
sanitizer = PromptSanitizer()

# Anonymize text
result = sanitizer.anonymize("Contact Lugnicca at lugnicca@gmail.com")
print(result.text)     # "Contact Lugnicca at __EMAIL_1__"
print(result.mapping)  # {"lugnicca@gmail.com": "__EMAIL_1__"}

# Deanonymize text
restored = sanitizer.deanonymize(result.text, result.mapping)
print(restored)  # "Contact Lugnicca at lugnicca@gmail.com"
```

### Custom Configuration

```python
from promptsan import PromptSanitizer, SanConfig

# Custom regex patterns
config = SanConfig(
    strategies=["regex"],
    regex_patterns={
        r'\b[A-Z][a-z]+ [A-Z][a-z]+\b': 'PERSON',
        r'\b\d{3}-\d{2}-\d{4}\b': 'SSN',
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b': 'EMAIL'
    }
)

sanitizer = PromptSanitizer(config)
result = sanitizer.anonymize("John Smith, SSN: 123-45-6789, email: john@company.com")
```

### Dictionary Strategy

```python
config = SanConfig(
    strategies=["dict"],
    custom_dict={
        "Project Alpha": "PROJECT",
        "CONFIDENTIAL": "CLASSIFICATION",
        "Acme Corp": "COMPANY"
    }
)

sanitizer = PromptSanitizer(config)
result = sanitizer.anonymize("CONFIDENTIAL: Project Alpha by Acme Corp")
```

### Combined Strategies

```python
config = SanConfig(
    strategies=["regex", "dict"],  # Applied in sequence
    custom_dict={"OpenAI": "AI_COMPANY"},
    regex_patterns={r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b': 'EMAIL'}
)

sanitizer = PromptSanitizer(config)
result = sanitizer.anonymize("OpenAI researcher at research@openai.com")
```

## 🤖 LLM Integration

PromptSan supports local LLM anonymization via LangChain:

```python
# Load prompt template
with open('examples/llm_prompt_basic.txt', 'r') as f:
    prompt_template = f.read()

config = SanConfig(
    strategies=["llm"],
    llm_model="dolphin3.0-llama3.1-8b",
    llm_base_url="http://localhost:1234/v1",
    llm_prompt_template=prompt_template
)

sanitizer = PromptSanitizer(config)
result = sanitizer.anonymize("Dr. Smith at General Hospital treats Keanu Reeves")
```

**Requirements:**
- Local LLM server (e.g., LM Studio, Ollama)
- Server running on `localhost:1234` (configurable)

## 🌊 Streaming Deanonymization

Perfect for real-time LLM output processing:

```python
def llm_response_stream():
    """Simulate LLM generating response with tokens"""
    yield "Patient __PERSON_1__ "
    yield "at __HOSPITAL_2__ "
    yield "has condition __CONDITION_3__"

# Deanonymize stream in real-time
mapping = {
    "Miyamoto Musashi": "__PERSON_1__",
    "General Hospital": "__HOSPITAL_2__", 
    "hypertension": "__CONDITION_3__"
}

sanitizer = PromptSanitizer()
deanonymized = sanitizer.deanonymize_stream(llm_response_stream(), mapping)

for chunk in deanonymized:
    print(chunk, end='', flush=True)
# Output: "Patient Miyamoto Musashi at General Hospital has condition hypertension"
```

(check examples/example_real_llm.py for a real-time LLM integration example)

## 🔧 Custom Strategies

Extend PromptSan with custom anonymization logic:

```python
from promptsan.mapping import MappingStore
import re

def credit_card_strategy(text: str, mapping: MappingStore, cfg: SanConfig) -> str:
    """Custom strategy for credit card numbers"""
    pattern = r'\b(?:4\d{3}|5[1-5]\d{2})\s?(?:\d{4}\s?){2}\d{4}\b'
    
    for match in re.finditer(pattern, text):
        cc_number = match.group().replace(' ', '')
        token = mapping.add(cc_number, "CREDIT_CARD")
        text = text.replace(match.group(), token)
    
    return text

# Register and use custom strategy
sanitizer = PromptSanitizer()
sanitizer.register_strategy("credit_card", credit_card_strategy)

config = SanConfig(strategies=["credit_card"])
sanitizer = PromptSanitizer(config)
sanitizer.register_strategy("credit_card", credit_card_strategy)

result = sanitizer.anonymize("Card: 4532 1234 5678 9012")
```

## 🖥️ Command Line Interface

PromptSan includes a CLI for quick operations:

```bash
# Anonymize text
promptsan anonymize --text "Lugnicca at lugnicca@gmail.com"

# Anonymize from file
promptsan anonymize --input-file document.txt --output-file anonymized.txt --mapping-file mapping.json

# Deanonymize text
promptsan deanonymize --text "__EMAIL_1__" --mapping-file mapping.json

# Stream deanonymize
promptsan stream-deanonymize --input-file stream.txt --mapping-file mapping.json

# Use custom configuration
promptsan --config examples/config_medical.json anonymize --input-file patient_data.txt
```

## Configuration Files

PromptSan includes ready-to-use configuration files:

### Provided Configurations

- `examples/config_basic.json` - Basic regex patterns (emails, phones, dates, ZIPs)
- `examples/config_enterprise.json` - Enterprise environment (classifications, employee IDs, references)
- `examples/config_medical.json` - Healthcare data (MRN, DOB, doctor names, hospitals)

### Using Configuration Files

```python
import json
from promptsan import PromptSanitizer, SanConfig

# Load a configuration file
with open('examples/config_medical.json', 'r') as f:
    config_data = json.load(f)

config = SanConfig(**config_data)
sanitizer = PromptSanitizer(config)

result = sanitizer.anonymize("Patient MRN: 123456, Dr. Smith at General Hospital")
```

### Custom Configuration

```json
{
  "strategies": ["regex", "dict"],
  "custom_dict": {
    "CONFIDENTIAL": "CLASSIFICATION",
    "Project Alpha": "PROJECT"
  },
  "regex_patterns": {
    "\\b[A-Z]{2,}\\d{6,8}\\b": "REFERENCE",
    "\\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}\\b": "EMAIL"
  },
  "llm_model": "dolphin3.0-llama3.1-8b",
  "llm_base_url": "http://localhost:1234/v1"
}
```

## 📚 Examples

The `examples/` directory contains comprehensive demonstrations:

- `example_basic_usage.py` - Getting started examples
- `example_advanced_strategies.py` - Dictionary and custom strategies
- `example_streaming.py` - Streaming deanonymization
- `example_llm_integration.py` - LLM-based anonymization
- `example_configuration.py` - Configuration patterns
- `example_config_files.py` - Using provided JSON config files
- `example_real_llm.py` - Real LLM integration (OpenAI/OpenRouter)
- `example_complete.py` - Full feature showcase

## 🏗️ Architecture

PromptSan follows a clean, minimal architecture:

```
promptsan/
├── __init__.py          # Public API
├── config.py            # Configuration dataclass
├── mapping.py           # Bidirectional entity mapping
├── strategies.py        # Anonymization strategies
├── sanitizer.py         # Main sanitizer class
└── cli.py              # Command-line interface
```

### Core Concepts

- **SanConfig**: Immutable configuration with Pydantic validation
- **MappingStore**: Bidirectional entity ↔ token mapping
- **AnonymizationStrategy**: Protocol for pluggable strategies
- **PromptSanitizer**: Main facade for all operations

## 🔒 Privacy & Security

- **Local Processing**: No data sent to external services (except configured LLM)
- **Reversible**: Perfect bidirectional mapping
- **Configurable**: Control exactly what gets anonymized
- **Auditable**: Clear mapping of what was changed

## 🎯 Use Cases

- **LLM Privacy**: Anonymize prompts before sending to cloud LLMs
- **Data Sharing**: Safe sharing of sensitive documents
- **Development**: Use real data structure with fake content
- **Compliance**: GDPR, HIPAA, SOX data protection
- **Testing**: Anonymize production data for testing

## 🧪 Testing

```bash
# Run example scripts
python examples/example_basic_usage.py
python examples/example_advanced_strategies.py
python examples/example_streaming.py
python examples/example_complete.py

# Run with custom configuration
python examples/example_llm_integration.py  # Requires local LLM
```

## 📋 Requirements

- Python 3.8+
- pydantic >= 2.0.0
- langchain >= 0.1.0 (for LLM strategy)
- langchain-openai >= 0.0.5 (for LLM strategy)
- openai >= 1.0.0 (for LLM strategy)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all examples work
5. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🔗 Links

- [GitHub Repository](https://github.com/lugnicca/prompt-san)
- [Documentation](https://github.com/lugnicca/prompt-san#readme)
- [Issues](https://github.com/lugnicca/prompt-san/issues)

## 🙏 Acknowledgments

- Built with [LangChain](https://langchain.com/) for LLM integration
- Validation powered by [Pydantic](https://pydantic.dev/)
- Inspired by privacy-first development practices

---

**PromptSan**: Minimal yet powerful text anonymization for the AI age.