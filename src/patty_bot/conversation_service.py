"""Application service for one customer conversation with Patty."""

from collections.abc import Iterable
import logging
from pathlib import Path

from patty_bot.agent_router import AgentTurn, ResponsesClient, create_openai_client, run_agent_turn
from patty_bot.application_errors import AgentProviderError, ConversationPersistenceError
from patty_bot.catalog import Product
from patty_bot.conversation import (
    ConversationMessage,
    ConversationState,
    ConversationStatus,
    allows_automatic_response,
    allows_order_modification,
    transition_status,
)
from patty_bot.conversation_repository import ConversationRepository, SQLiteConversationRepository
from patty_bot.config import LLMConfigurationError, LLMSettings, load_llm_settings
from patty_bot.orders import OrderDetails
from patty_bot.tool_executor import AgentSession


LOGGER = logging.getLogger(__name__)
SAFE_PROVIDER_REPLY = "No pude responder en este momento. Intenta nuevamente en unos instantes."


class ConversationService:
    """Own the provider lifecycle and route customer messages to the agent."""

    def __init__(
        self,
        products: Iterable[Product],
        database_path: Path,
        repository: ConversationRepository | None = None,
    ) -> None:
        self._products = tuple(products)
        self._database_path = database_path
        self._repository = repository or SQLiteConversationRepository(database_path)
        self._client: ResponsesClient | None = None
        self._client_key: str | None = None

    def load_conversation(self, conversation_id: str) -> ConversationState:
        """Load persisted state or create the initial state for a new conversation."""

        state = self._load_state(conversation_id, stage="load_conversation")
        if state is not None:
            normalized_state = self._confirmed_state(state)
            if normalized_state != state:
                self._save_state(normalized_state, stage="normalize_conversation")
            LOGGER.info("conversation loaded [conversation_id=%s stage=load_conversation]", conversation_id)
            return normalized_state
        state = ConversationState(
            conversation_id=conversation_id,
            order_details=OrderDetails(),
        )
        self._save_state(state, stage="create_conversation")
        LOGGER.info("conversation created [conversation_id=%s stage=create_conversation]", conversation_id)
        return state

    def save_conversation(self, conversation_state: ConversationState) -> ConversationState:
        """Persist state updated by a channel-owned UI control."""

        current_state = self._load_state(conversation_state.conversation_id, stage="save_conversation")
        if current_state is not None and not allows_order_modification(current_state.status):
            if _order_state_changed(current_state, conversation_state):
                raise ValueError(f"Conversation {current_state.status.value} does not allow order modifications.")
        normalized_state = self._confirmed_state(conversation_state)
        self._save_state(normalized_state, stage="save_conversation")
        return normalized_state

    def transition_conversation(self, conversation_id: str, target: ConversationStatus) -> ConversationState:
        """Apply one valid operational transition and persist its resulting state."""

        state = self.load_conversation(conversation_id)
        updated_state = ConversationState(
            conversation_id=state.conversation_id,
            status=transition_status(state.status, target),
            cart=state.cart,
            order_details=state.order_details,
            confirmed_order=state.confirmed_order,
            messages=state.messages,
        )
        self._save_state(updated_state, stage="transition_conversation")
        LOGGER.info(
            "conversation transitioned [conversation_id=%s stage=transition_conversation status=%s]",
            conversation_id,
            target.value,
        )
        return updated_state

    def handle_message(
        self,
        conversation_id: str,
        user_message: str,
    ) -> AgentTurn:
        """Return the reply and updated session for a single customer message."""

        LOGGER.info("conversation turn started [conversation_id=%s stage=handle_message]", conversation_id)
        try:
            state = self.load_conversation(conversation_id)
        except ConversationPersistenceError:
            return AgentTurn(reply=SAFE_PROVIDER_REPLY, session=self._empty_session())
        session = self._agent_session(state)
        if not allows_automatic_response(state.status):
            self._save_handoff_message(state, user_message)
            return AgentTurn(reply="", session=session)
        conversation = tuple({"role": message.role, "content": message.content} for message in state.messages)
        try:
            settings = load_llm_settings()
        except LLMConfigurationError:
            LOGGER.warning("LLM configuration unavailable [conversation_id=%s stage=load_settings]", conversation_id)
            return self._persist_turn(
                state,
                reply="El chat con Patty aun no esta configurado. Completa las variables del LLM para activarlo.",
                session=session,
                user_message=user_message,
            )

        if self._client is None or self._client_key != settings.api_key:
            try:
                self._client = create_openai_client(settings)
                self._client_key = settings.api_key
            except RuntimeError as error:
                self._log_provider_error(conversation_id, "create_client", error)
                return self._persist_turn(
                    state,
                    reply="Falta instalar la dependencia de OpenAI. Ejecuta la instalacion del proyecto nuevamente.",
                    session=session,
                    user_message=user_message,
                )
            except Exception as error:
                self._log_provider_error(conversation_id, "create_client", error)
                return self._persist_turn(
                    state,
                    reply=SAFE_PROVIDER_REPLY,
                    session=session,
                    user_message=user_message,
                )

        try:
            LOGGER.info("agent execution started [conversation_id=%s stage=run_agent_turn]", conversation_id)
            turn = self._run_agent_turn(
                conversation_id,
                self._client,
                settings,
                session,
                user_message,
                conversation,
            )
            return self._persist_turn(state, reply=turn.reply, session=turn.session, user_message=user_message)
        except AgentProviderError:
            return self._persist_turn(
                state,
                reply=SAFE_PROVIDER_REPLY,
                session=session,
                user_message=user_message,
            )

    def _agent_session(self, state: ConversationState) -> AgentSession:
        return AgentSession(
            products=self._products,
            database_path=self._database_path,
            cart=state.cart,
            order_details=state.order_details,
            confirmed_order=state.confirmed_order,
        )

    def _empty_session(self) -> AgentSession:
        return AgentSession(products=self._products, database_path=self._database_path)

    def _persist_turn(
        self,
        state: ConversationState,
        *,
        reply: str,
        session: AgentSession,
        user_message: str = "",
    ) -> AgentTurn:
        messages = state.messages
        if user_message:
            messages += (ConversationMessage(role="user", content=user_message),)
        updated_state = ConversationState(
            conversation_id=state.conversation_id,
            status=self._status_after_turn(state.status, session),
            cart=session.cart,
            order_details=session.order_details,
            confirmed_order=session.confirmed_order,
            messages=messages + (ConversationMessage(role="assistant", content=reply),),
        )
        try:
            self._save_state(updated_state, stage="persist_turn")
        except ConversationPersistenceError:
            return AgentTurn(reply=SAFE_PROVIDER_REPLY, session=session)
        return AgentTurn(reply=reply, session=session)

    def _load_state(self, conversation_id: str, *, stage: str) -> ConversationState | None:
        try:
            return self._repository.load(conversation_id)
        except Exception as error:
            self._log_persistence_error(conversation_id, stage, error)
            raise ConversationPersistenceError("Conversation state could not be loaded.") from error

    def _save_state(self, state: ConversationState, *, stage: str) -> None:
        try:
            self._repository.save(state)
        except Exception as error:
            self._log_persistence_error(state.conversation_id, stage, error)
            raise ConversationPersistenceError("Conversation state could not be saved.") from error
        LOGGER.info("conversation persisted [conversation_id=%s stage=%s]", state.conversation_id, stage)

    def _run_agent_turn(
        self,
        conversation_id: str,
        client: ResponsesClient,
        settings: LLMSettings,
        session: AgentSession,
        user_message: str,
        conversation: tuple[dict[str, str], ...],
    ) -> AgentTurn:
        try:
            return run_agent_turn(client, settings, session, user_message, conversation)
        except Exception as error:
            self._log_provider_error(conversation_id, "run_agent_turn", error)
            raise AgentProviderError("The LLM provider could not complete the turn.") from error

    def _save_handoff_message(self, state: ConversationState, user_message: str) -> None:
        try:
            self._save_state(
                ConversationState(
                    conversation_id=state.conversation_id,
                    status=state.status,
                    cart=state.cart,
                    order_details=state.order_details,
                    confirmed_order=state.confirmed_order,
                    messages=state.messages + (ConversationMessage(role="user", content=user_message),),
                ),
                stage="persist_handoff_message",
            )
        except ConversationPersistenceError:
            # The handoff has no automatic response, so persistence remains the only action to protect.
            return

    def _log_persistence_error(self, conversation_id: str, stage: str, error: Exception) -> None:
        LOGGER.error(
            "conversation persistence error [conversation_id=%s stage=%s error_type=%s]",
            conversation_id,
            stage,
            type(error).__name__,
        )

    def _log_provider_error(self, conversation_id: str, stage: str, error: Exception) -> None:
        LOGGER.error(
            "agent provider error [conversation_id=%s stage=%s error_type=%s]",
            conversation_id,
            stage,
            type(error).__name__,
        )

    def _confirmed_state(self, state: ConversationState) -> ConversationState:
        if state.confirmed_order is None:
            return state
        return ConversationState(
            conversation_id=state.conversation_id,
            status=self._status_after_turn(state.status, self._agent_session(state)),
            cart=state.cart,
            order_details=state.order_details,
            confirmed_order=state.confirmed_order,
            messages=state.messages,
        )

    def _status_after_turn(self, status: ConversationStatus, session: AgentSession) -> ConversationStatus:
        if session.confirmed_order is None or status == ConversationStatus.CONFIRMED:
            return status
        if status == ConversationStatus.ACTIVE:
            status = transition_status(status, ConversationStatus.AWAITING_CONFIRMATION)
        return transition_status(status, ConversationStatus.CONFIRMED)


def _order_state_changed(current: ConversationState, updated: ConversationState) -> bool:
    return (
        current.cart != updated.cart
        or current.order_details != updated.order_details
        or current.confirmed_order != updated.confirmed_order
    )
