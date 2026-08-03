"""Small error hierarchy for application-layer boundaries."""


class ConversationError(RuntimeError):
    """Base error for failures while handling a customer conversation."""


class ConversationPersistenceError(ConversationError):
    """Raised when conversation state cannot be loaded or saved."""


class AgentProviderError(ConversationError):
    """Raised when the configured LLM provider cannot complete a turn."""
