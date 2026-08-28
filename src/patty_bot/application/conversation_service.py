"""Application service for one customer conversation with Patty."""

from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
import logging
from pathlib import Path
import re
from uuid import uuid4

from patty_bot.agent.router import AgentTurn, ResponsesClient, create_openai_client, run_agent_turn
from patty_bot.application.errors import AgentProviderError, ConversationPersistenceError
from patty_bot.application.handoff_policy import decide_handoff
from patty_bot.application.handoff_presentation import HORECA_OR_SPECIAL_ORDER_HANDOFF_MESSAGE
from patty_bot.domain.catalog import Product
from patty_bot.application.conversation_state import (
    ConversationMessage,
    ConversationState,
    ConversationStatus,
    HandoffReason,
    PendingMessage,
    allows_automatic_response,
    allows_order_modification,
    transition_status,
    transition_to_human_handoff,
)
from patty_bot.infrastructure.conversation_repository import ConversationRepository, SQLiteConversationRepository
from patty_bot.infrastructure.config import LLMConfigurationError, LLMSettings, load_llm_settings
from patty_bot.domain.orders import OrderDetails
from patty_bot.agent.tool_executor import AgentSession


LOGGER = logging.getLogger(__name__)
SAFE_PROVIDER_REPLY = "No pude responder en este momento. Intenta nuevamente en unos instantes."
HUMAN_HANDOFF_REPLY = "Voy a derivar tu conversacion a una persona del equipo para que pueda ayudarte."
MESSAGE_DEBOUNCE_WINDOW = timedelta(seconds=3)
_IMMEDIATE_MESSAGE_PATTERN = re.compile(r"\b(confirmo|confirmar|cancelar|anular)\b", re.IGNORECASE)


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
            handoff_reason=state.handoff_reason,
            pending_messages=state.pending_messages,
            pending_until=state.pending_until,
            processing_batch=state.processing_batch,
        )
        self._save_state(updated_state, stage="transition_conversation")
        LOGGER.info(
            "conversation transitioned [conversation_id=%s stage=transition_conversation status=%s]",
            conversation_id,
            target.value,
        )
        return updated_state

    def initiate_human_handoff(
        self,
        conversation_id: str,
        reason: HandoffReason,
        *,
        user_message: str | None = None,
    ) -> ConversationState:
        """Transfer a conversation to a human and persist its resumable context.

        A channel adapter or a future router must supply the structured reason.
        The optional triggering customer message is retained alongside the prior
        conversation history so an operator can resume without asking the
        customer to repeat it.  This method intentionally contains no policy
        for deciding *when* a handoff is necessary.
        """

        state = self.load_conversation(conversation_id)
        updated_state = ConversationState(
            conversation_id=state.conversation_id,
            status=transition_to_human_handoff(state.status, reason),
            cart=state.cart,
            order_details=state.order_details,
            confirmed_order=state.confirmed_order,
            messages=state.messages
            + ((ConversationMessage(role="user", content=user_message),) if user_message is not None else ()),
            handoff_reason=reason,
            pending_messages=state.pending_messages,
            pending_until=state.pending_until,
            processing_batch=state.processing_batch,
        )
        self._save_state(updated_state, stage="initiate_human_handoff")
        LOGGER.info(
            "human handoff initiated [conversation_id=%s stage=initiate_human_handoff reason=%s]",
            conversation_id,
            reason.value,
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
        handoff = decide_handoff(state, user_message)
        if handoff is not None:
            return self._initiate_detected_handoff(state, user_message, handoff.reason)
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
            return self._initiate_detected_handoff(state, user_message, HandoffReason.PROCESSING_ERROR)

    def queue_message(self, conversation_id: str, user_message: str, *, now: datetime | None = None) -> bool:
        """Persist a customer message and return whether it was handled immediately.

        Channels call this method when they can accept several messages before a
        reply. The message itself is persisted immediately; only the provider
        call waits for the short sliding window.
        """

        now = now or datetime.now(UTC)
        try:
            state = self.load_conversation(conversation_id)
            if not allows_automatic_response(state.status):
                self._save_handoff_message(state, user_message)
                return True
            handoff = decide_handoff(state, user_message)
            if handoff is not None:
                self._handoff_buffered_messages(state, user_message, handoff.reason)
                return True
            pending = PendingMessage(id=str(uuid4()), content=user_message, received_at=now)
            self._repository.enqueue_pending_message(conversation_id, pending, now + MESSAGE_DEBOUNCE_WINDOW)
            if _IMMEDIATE_MESSAGE_PATTERN.search(user_message):
                self.process_due_messages(conversation_id, now=now, force=True)
                return True
            return False
        except ConversationPersistenceError:
            return True
        except Exception as error:
            self._log_persistence_error(conversation_id, "queue_message", error)
            return True

    def process_due_messages(
        self, conversation_id: str, *, now: datetime | None = None, force: bool = False
    ) -> AgentTurn | None:
        """Process one exclusively claimed debounce batch when it is due."""

        now = now or datetime.now(UTC)
        try:
            state = self._repository.claim_pending_messages(conversation_id, now, force=force)
        except Exception as error:
            self._log_persistence_error(conversation_id, "claim_pending_messages", error)
            return AgentTurn(reply=SAFE_PROVIDER_REPLY, session=self._empty_session())
        if state is None:
            return None
        batch = state.processing_batch
        if batch is None:
            return None
        session = self._agent_session(state)
        user_message = "\n".join(message.content for message in batch.messages)
        conversation = tuple({"role": message.role, "content": message.content} for message in state.messages)
        try:
            settings = load_llm_settings()
            if self._client is None or self._client_key != settings.api_key:
                self._client = create_openai_client(settings)
                self._client_key = settings.api_key
            turn = self._run_agent_turn(conversation_id, self._client, settings, session, user_message, conversation)
            persisted = self._repository.complete_pending_messages(conversation_id, batch.id, turn.reply, self._state_after_turn(state, turn.session))
            return AgentTurn(reply=turn.reply, session=self._agent_session(persisted))
        except LLMConfigurationError:
            return self._complete_buffered_reply(state, batch.id, session, "El chat con Patty aun no esta configurado. Completa las variables del LLM para activarlo.")
        except AgentProviderError:
            return self._complete_buffered_handoff(state, batch.id, HandoffReason.PROCESSING_ERROR)
        except RuntimeError as error:
            self._log_provider_error(conversation_id, "create_client", error)
            return self._complete_buffered_reply(state, batch.id, session, "Falta instalar la dependencia de OpenAI. Ejecuta la instalacion del proyecto nuevamente.")
        except Exception as error:
            self._log_persistence_error(conversation_id, "complete_pending_messages", error)
            return AgentTurn(reply=SAFE_PROVIDER_REPLY, session=session)

    def _initiate_detected_handoff(
        self,
        state: ConversationState,
        user_message: str,
        reason: HandoffReason,
    ) -> AgentTurn:
        """Persist a policy-selected handoff without entering the provider path."""

        try:
            updated_state = self.initiate_human_handoff(
                state.conversation_id,
                reason,
                user_message=user_message,
            )
        except ConversationPersistenceError:
            return AgentTurn(reply=SAFE_PROVIDER_REPLY, session=self._agent_session(state))
        reply = (
            HORECA_OR_SPECIAL_ORDER_HANDOFF_MESSAGE
            if reason is HandoffReason.HORECA_OR_SPECIAL_ORDER
            else HUMAN_HANDOFF_REPLY
        )
        return AgentTurn(reply=reply, session=self._agent_session(updated_state))

    def _handoff_buffered_messages(self, state: ConversationState, user_message: str, reason: HandoffReason) -> None:
        """Keep any waiting customer messages visible when a human takes over."""

        self._repository.handoff_pending_messages(state.conversation_id, user_message, reason)

    def _complete_buffered_reply(
        self, state: ConversationState, batch_id: str, session: AgentSession, reply: str
    ) -> AgentTurn:
        try:
            persisted = self._repository.complete_pending_messages(
                state.conversation_id, batch_id, reply, self._state_after_turn(state, session)
            )
        except Exception as error:
            self._log_persistence_error(state.conversation_id, "complete_pending_messages", error)
            return AgentTurn(reply=SAFE_PROVIDER_REPLY, session=session)
        return AgentTurn(reply=reply, session=self._agent_session(persisted))

    def _complete_buffered_handoff(self, state: ConversationState, batch_id: str, reason: HandoffReason) -> AgentTurn:
        handoff_state = ConversationState(
            conversation_id=state.conversation_id,
            status=transition_to_human_handoff(state.status, reason),
            cart=state.cart,
            order_details=state.order_details,
            confirmed_order=state.confirmed_order,
            messages=state.messages,
            handoff_reason=reason,
        )
        try:
            persisted = self._repository.complete_pending_messages(
                state.conversation_id, batch_id, HUMAN_HANDOFF_REPLY, handoff_state
            )
        except Exception as error:
            self._log_persistence_error(state.conversation_id, "complete_pending_handoff", error)
            return AgentTurn(reply=SAFE_PROVIDER_REPLY, session=self._agent_session(state))
        return AgentTurn(reply=HUMAN_HANDOFF_REPLY, session=self._agent_session(persisted))

    def _state_after_turn(self, state: ConversationState, session: AgentSession) -> ConversationState:
        return ConversationState(
            conversation_id=state.conversation_id,
            status=self._status_after_turn(state.status, session),
            cart=session.cart,
            order_details=session.order_details,
            confirmed_order=session.confirmed_order,
            messages=state.messages,
            handoff_reason=state.handoff_reason,
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
            handoff_reason=state.handoff_reason,
            pending_messages=state.pending_messages,
            pending_until=state.pending_until,
            processing_batch=state.processing_batch,
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
                    handoff_reason=state.handoff_reason,
                    pending_messages=state.pending_messages,
                    pending_until=state.pending_until,
                    processing_batch=state.processing_batch,
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
            handoff_reason=state.handoff_reason,
            pending_messages=state.pending_messages,
            pending_until=state.pending_until,
            processing_batch=state.processing_batch,
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
