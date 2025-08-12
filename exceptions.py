"""Custom exception classes for the application."""

class OllamaConnectionError(Exception):
    """Raised when the application cannot connect to the Ollama server."""
    pass

class OllamaVersionError(Exception):
    """Raised when the Ollama server version is not supported."""
    pass

class OllamaRequestError(Exception):
    """Raised for errors that occur during a request to the Ollama API."""
    pass

class LLMResponseError(Exception):
    """Raised when the LLM response is malformed or invalid."""
    pass

class DatabaseQueryError(Exception):
    """Raised for errors that occur during database query execution."""
    pass
