import random
import string
import hashlib
import base64

import tiktoken


def merge_dicts(dict1: dict, dict2: dict) -> dict:
    """Recursively merge two dictionaries with list handling."""
    result = dict1.copy()

    for key, value in dict2.items():
        if key in result:
            if isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = merge_dicts(result[key], value)
            elif isinstance(result[key], list) and isinstance(value, list):
                result[key] = result[key] + value
            else:
                result[key] = value
        else:
            result[key] = value

    return result


def generate_random_hex(length: int) -> str:
    """Generate a random hex string of specified length.

    Args:
        length: The desired length of the hex string.

    Returns:
        str: Random hex string of the specified length.
    """

    hex_chars = string.hexdigits.lower()
    return "".join(random.choice(hex_chars) for _ in range(length))


def clip_tokens(text: str, max_tokens: int, model_id: str) -> str:
    """Clip the text to a maximum number of tokens using the tiktoken tokenizer.

    Args:
        text: The input text to clip.
        max_tokens: Maximum number of tokens to keep (default: 8192).
        model_id: The model name to determine encoding (default: "gpt-4").

    Returns:
        str: The clipped text that fits within the token limit.
    """

    try:
        encoding = tiktoken.encoding_for_model(model_id)
    except KeyError:
        # Fallback to cl100k_base encoding (used by gpt-4, gpt-3.5-turbo, text-embedding-ada-002)
        encoding = tiktoken.get_encoding("cl100k_base")

    tokens = encoding.encode(text)
    if len(tokens) <= max_tokens:
        return text

    return encoding.decode(tokens[:max_tokens])


def generate_content_hash(content: str, length: int = 32) -> str:
    """Generate a hash of the content using SHA-256 and convert to base64.
    
    Args:
        content: The content string to hash.
        length: The desired length of the final hash (truncated from base64).
        
    Returns:
        str: A base64 hash of the content, truncated to the specified length.
    """
    # Generate SHA-256 hash of the content
    content_hash = hashlib.sha256(content.encode('utf-8')).digest()
    
    # Convert to base64 and remove padding characters
    base64_hash = base64.urlsafe_b64encode(content_hash).decode('utf-8').rstrip('=')
    
    # Truncate to desired length if needed
    if length and len(base64_hash) > length:
        base64_hash = base64_hash[:length]
    
    return base64_hash
