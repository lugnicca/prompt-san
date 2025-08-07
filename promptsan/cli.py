"""
Command-line interface for PromptSan

Provides CLI commands for anonymization, deanonymization, and streaming
operations with support for file I/O and flexible configuration.
"""

import argparse
import json
import sys
import typing

from .config import SanConfig
from .sanitizer import PromptSanitizer


def main() -> None:
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="PromptSan: Text anonymization and deanonymization CLI",
        epilog="Examples:\n"
        "  promptsan anonymize --text 'John lives at john@email.com'\n"
        "  promptsan deanonymize --text '__EMAIL_1__' --mapping-file mapping.json\n"
        "  echo 'sensitive data' | promptsan anonymize",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--config", type=str, help="JSON config file for SanConfig")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Anonymize command
    anon_parser = subparsers.add_parser("anonymize", help="Anonymize text")
    anon_parser.add_argument("--text", type=str, help="Text to anonymize")
    anon_parser.add_argument("--input-file", type=str, help="Input file path")
    anon_parser.add_argument(
        "--output-file", type=str, help="Output file for anonymized text"
    )
    anon_parser.add_argument(
        "--mapping-file", type=str, help="Output file for mapping JSON"
    )
    anon_parser.add_argument(
        "--strategies",
        type=str,
        default=None,
        help="Comma-separated strategies (override config)",
    )
    anon_parser.add_argument(
        "--custom-dict",
        type=str,
        default="{}",
        help="JSON dict for custom replacements",
    )
    anon_parser.add_argument(
        "--dict-case-insensitive",
        action="store_true",
        help="Dictionary strategy: case-insensitive matching",
    )
    anon_parser.add_argument(
        "--dict-no-word-boundaries",
        action="store_true",
        help="Dictionary strategy: disable word boundary anchors",
    )
    anon_parser.add_argument(
        "--llm-model", type=str, default="dolphin3.0-llama3.1-8b", help="LLM model name"
    )
    anon_parser.add_argument(
        "--llm-base-url",
        type=str,
        default="http://localhost:1234/v1",
        help="LLM base URL",
    )
    anon_parser.add_argument(
        "--llm-prompt-template", type=str, help="Custom LLM prompt template"
    )
    anon_parser.add_argument(
        "--json", action="store_true", help="Output machine-readable JSON"
    )

    # Deanonymize command
    deanon_parser = subparsers.add_parser("deanonymize", help="Deanonymize text")
    deanon_parser.add_argument("--text", type=str, help="Text to deanonymize")
    deanon_parser.add_argument("--input-file", type=str, help="Input file path")
    deanon_parser.add_argument(
        "--output-file", type=str, help="Output file for deanonymized text"
    )
    deanon_parser.add_argument(
        "--mapping-file", type=str, required=True, help="Mapping JSON file"
    )

    # Stream deanonymize command
    stream_parser = subparsers.add_parser(
        "stream-deanonymize", help="Deanonymize streaming text"
    )
    stream_parser.add_argument("--input-file", type=str, help="Input file path")
    stream_parser.add_argument(
        "--output-file", type=str, help="Output file for deanonymized text"
    )
    stream_parser.add_argument(
        "--mapping-file", type=str, required=True, help="Mapping JSON file"
    )
    stream_parser.add_argument(
        "--chunk-size", type=int, default=100, help="Chunk size for streaming"
    )

    args = parser.parse_args()

    # Load config if provided
    config = SanConfig()
    if args.config:
        try:
            with open(args.config, "r") as f:
                config_data = json.load(f)
            config = SanConfig(**config_data)
        except (FileNotFoundError, json.JSONDecodeError, TypeError) as e:
            print(f"Error loading config file: {e}", file=sys.stderr)
            sys.exit(1)

    try:
        if args.command == "anonymize":
            _handle_anonymize(args, config)
        elif args.command == "deanonymize":
            _handle_deanonymize(args)
        elif args.command == "stream-deanonymize":
            _handle_stream_deanonymize(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def _handle_anonymize(args: argparse.Namespace, base_config: SanConfig) -> None:
    """Handle anonymize command"""
    # Get input text
    if args.input_file:
        with open(args.input_file, "r", encoding="utf-8") as f:
            text = f.read()
    elif args.text:
        text = args.text
    else:
        text = sys.stdin.read()

    if args.verbose:
        print(f"Strategies: {args.strategies}", file=sys.stderr)

    # Parse custom dict
    try:
        custom_dict = json.loads(args.custom_dict)
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON for --custom-dict")

    # Override config with CLI arguments (only if explicitly set)
    config = SanConfig(
        strategies=(
            args.strategies.split(",") if args.strategies else base_config.strategies
        ),
        llm_model=(
            args.llm_model
            if args.llm_model != "dolphin3.0-llama3.1-8b"
            else base_config.llm_model
        ),
        custom_dict=(
            custom_dict if args.custom_dict != "{}" else base_config.custom_dict
        ),
        regex_patterns=base_config.regex_patterns,
        llm_base_url=(
            args.llm_base_url
            if args.llm_base_url != "http://localhost:1234/v1"
            else base_config.llm_base_url
        ),
        llm_prompt_template=(
            args.llm_prompt_template
            if args.llm_prompt_template
            else base_config.llm_prompt_template
        ),
        dict_case_insensitive=args.dict_case_insensitive
        or getattr(base_config, "dict_case_insensitive", False),
        dict_use_word_boundaries=(
            not args.dict_no_word_boundaries
            if args.dict_no_word_boundaries
            else getattr(base_config, "dict_use_word_boundaries", True)
        ),
    )

    # Anonymize
    sanitizer = PromptSanitizer(config)
    result = sanitizer.anonymize(text)

    # Output
    if args.json:
        output_obj = {"text": result.text, "mapping": result.mapping}
        print(json.dumps(output_obj, ensure_ascii=False))
    else:
        if args.output_file:
            with open(args.output_file, "w", encoding="utf-8") as f:
                f.write(result.text)
        else:
            print(result.text)

        # Output mapping
        mapping_json = json.dumps(result.mapping, indent=2)
        if args.mapping_file:
            with open(args.mapping_file, "w", encoding="utf-8") as f:
                f.write(mapping_json)
        elif not args.output_file and args.verbose:
            print("Mapping:", mapping_json, file=sys.stderr)


def _handle_deanonymize(args: argparse.Namespace) -> None:
    """Handle deanonymize command"""
    # Get input text
    if args.input_file:
        with open(args.input_file, "r", encoding="utf-8") as f:
            text = f.read()
    elif args.text:
        text = args.text
    else:
        text = sys.stdin.read()

    # Load mapping
    with open(args.mapping_file, "r", encoding="utf-8") as f:
        mapping = json.load(f)

    # Deanonymize
    sanitizer = PromptSanitizer()
    result = sanitizer.deanonymize(text, mapping)

    # Output
    if args.output_file:
        with open(args.output_file, "w", encoding="utf-8") as f:
            f.write(result)
    else:
        print(result)


def _handle_stream_deanonymize(args: argparse.Namespace) -> None:
    """Handle stream-deanonymize command"""
    # Load mapping
    with open(args.mapping_file, "r", encoding="utf-8") as f:
        mapping = json.load(f)

    # Create text generator
    def text_generator() -> "typing.Generator[str, None, None]":
        if args.input_file:
            with open(args.input_file, "r", encoding="utf-8") as f:
                while True:
                    chunk = f.read(args.chunk_size)
                    if not chunk:
                        break
                    yield chunk
        else:
            # Read from stdin in chunks
            while True:
                chunk = sys.stdin.read(args.chunk_size)
                if not chunk:
                    break
                yield chunk

    # Deanonymize stream
    sanitizer = PromptSanitizer()
    deanonymized_stream = sanitizer.deanonymize_stream(text_generator(), mapping)

    # Output
    if args.output_file:
        with open(args.output_file, "w", encoding="utf-8") as f:
            for chunk in deanonymized_stream:
                f.write(chunk)
    else:
        for chunk in deanonymized_stream:
            print(chunk, end="")


if __name__ == "__main__":
    main()
