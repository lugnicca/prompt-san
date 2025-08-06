"""
Mapping module for PromptSan

Handles bidirectional mapping between original entities and anonymization tokens.
Supports both batch deanonymization and streaming deanonymization for real-time
processing.
"""

from typing import Dict, Generator


class MappingStore:
    """
    Bidirectional mapping store for entity <-> token relationships
    
    Maintains two dictionaries:
    - e2t: entity -> token mapping
    - t2e: token -> entity mapping (reverse lookup)
    
    Thread-safe for read operations, but not for concurrent writes.
    """
    
    def __init__(self):
        self.e2t: Dict[str, str] = {}  # entity -> token
        self.t2e: Dict[str, str] = {}  # token -> entity
        self._counters: Dict[str, int] = {}  # label -> counter
    
    def add(self, entity: str, label: str) -> str:
        """
        Add an entity to the mapping store or return existing token
        
        Args:
            entity: Original text to anonymize
            label: Category label for the entity (e.g., "EMAIL", "PERSON")
            
        Returns:
            Token in format __LABEL_N__ where N is an incrementing counter
        """
        if entity in self.e2t:
            return self.e2t[entity]
        
        # Generate new token
        counter = self._counters.get(label, 0) + 1
        self._counters[label] = counter
        token = f"__{label}_{counter}__"
        
        # Store bidirectional mapping
        self.e2t[entity] = token
        self.t2e[token] = entity
        
        return token
    
    def deanonymize(self, text: str) -> str:
        """
        Replace all tokens in text with their original entities
        
        Args:
            text: Text containing anonymization tokens
            
        Returns:
            Text with tokens replaced by original entities
        """
        for token, entity in self.t2e.items():
            text = text.replace(token, entity)
        return text
    
    def deanonymize_stream(self, gen: Generator[str, None, None]) -> Generator[str, None, None]:
        """
        Deanonymize text from a generator stream, handling partial tokens
        
        Args:
            gen: Generator yielding text chunks
            
        Yields:
            Chunks with tokens replaced by original entities
            
        Note:
            Handles cases where tokens are split across chunk boundaries
        """
        buffer = ''
        tokens_to_check = sorted(self.t2e.items(), key=lambda x: -len(x[0]))  # Longest first
        max_token_length = max(len(token) for token, _ in tokens_to_check) if tokens_to_check else 0
        
        for chunk in gen:
            buffer += chunk
            output = ''
            i = 0
            
            # Process the buffer, but keep potential partial tokens at the end
            while i <= len(buffer) - max_token_length:
                matched = False
                # Try to match tokens at current position
                for token, entity in tokens_to_check:
                    if buffer.startswith(token, i):
                        output += entity
                        i += len(token)
                        matched = True
                        break
                
                if not matched:
                    output += buffer[i]
                    i += 1
            
            # Yield the processed output (if any)
            if output:
                yield output
            
            # Keep the unprocessed suffix as buffer (potential partial tokens)
            buffer = buffer[i:]
        
        # Final flush: process remaining buffer completely
        if buffer:
            final_output = self.deanonymize(buffer)
            if final_output:
                yield final_output

    @classmethod
    def from_dict(cls, mapping: Dict[str, str]) -> 'MappingStore':
        """
        Create MappingStore from entity->token dictionary
        
        Args:
            mapping: Dictionary of entity->token mappings
            
        Returns:
            New MappingStore instance with loaded mappings
        """
        instance = cls()
        instance.e2t = mapping
        instance.t2e = {token: entity for entity, token in mapping.items()}
        return instance