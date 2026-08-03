from datetime import date
from dataclasses import replace
from uuid import uuid4

import streamlit as st

from patty_bot.domain.cart import add_product_to_cart, change_cart_item_quantity, remove_product_from_cart
from patty_bot.domain.catalog import CatalogSearchResult, load_catalog, search_products
from patty_bot.application.logging import configure_application_logging
from patty_bot.infrastructure.config import (
    APP_TITLE,
    CATALOG_SAMPLE_PATH,
    DATABASE_PATH,
    PICKUP_STORES,
)
from patty_bot.application.conversation_state import ConversationState
from patty_bot.application.conversation_service import ConversationService
from patty_bot.domain.orders import (
    OrderDetails,
    delivery_fee_for_order,
    total_for_order,
    validate_order_details,
)
from patty_bot.infrastructure.repository import save_confirmed_order
def initialize_session_state(catalog) -> None:
    """Initialize UI state while ConversationService owns agent execution details."""

    if "conversation_service" not in st.session_state:
        st.session_state.conversation_service = ConversationService(catalog, DATABASE_PATH)
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = str(uuid4())
    if "conversation_state" not in st.session_state:
        st.session_state.conversation_state = st.session_state.conversation_service.load_conversation(
            st.session_state.conversation_id
        )


def persist_conversation_state(state: ConversationState) -> None:
    """Keep the UI cache aligned after a non-chat interaction changes the conversation."""

    st.session_state.conversation_state = st.session_state.conversation_service.save_conversation(state)


@st.cache_data
def get_catalog():
    # The sample catalog is immutable during a Streamlit session, so avoid re-reading its CSV on reruns.
    return load_catalog(CATALOG_SAMPLE_PATH)


def format_price(value) -> str:
    return f"S/ {value:.2f}"


def render_catalog_result(result: CatalogSearchResult, catalog, disabled: bool = False) -> None:
    if not result.query.strip():
        st.info("Escribe una busqueda para consultar el catalogo.")
        return

    if not result.found:
        st.warning("No encontramos ese producto en el catalogo sample de Patty.")
        return

    for match in result.matches:
        product = match.product
        columns = st.columns([3, 1, 1])
        with columns[0]:
            st.write(f"**{product.name}**")
            st.caption(f"{product.category} - {match.match_type} - score {match.score:.2f}")
        with columns[1]:
            st.write(format_price(product.price))
        with columns[2]:
            if st.button("Agregar", key=f"add-{product.id}", disabled=disabled):
                # Cart mutations stay in the domain layer; the UI only stores the returned immutable cart.
                state = st.session_state.conversation_state
                persist_conversation_state(
                    replace(
                        state,
                        cart=add_product_to_cart(state.cart, catalog, product.id),
                    )
                )
                st.rerun()


def render_cart(order_details: OrderDetails, disabled: bool = False) -> None:
    st.subheader("Carrito")
    state = st.session_state.conversation_state
    cart = state.cart

    if cart.is_empty:
        st.info("El carrito esta vacio.")
        return

    for item in cart.items:
        columns = st.columns([3, 1, 1, 1])
        with columns[0]:
            st.write(f"**{item.product.name}**")
            st.caption(format_price(item.product.price))
        with columns[1]:
            quantity = st.number_input(
                "Cantidad",
                min_value=1,
                step=1,
                value=item.quantity,
                # Include the quantity in the key so Streamlit does not reuse stale widget state after updates.
                key=f"quantity-{item.product.id}-{item.quantity}",
                disabled=disabled,
            )
            if not disabled and quantity != item.quantity:
                persist_conversation_state(
                    replace(
                        state,
                        cart=change_cart_item_quantity(cart, item.product.id, int(quantity)),
                    )
                )
                st.rerun()
        with columns[2]:
            st.write(format_price(item.line_subtotal))
        with columns[3]:
            if st.button("Quitar", key=f"remove-{item.product.id}", disabled=disabled):
                persist_conversation_state(
                    replace(
                        state,
                        cart=remove_product_from_cart(cart, item.product.id),
                    )
                )
                st.rerun()

    st.metric("Subtotal", format_price(cart.subtotal))
    st.metric("Delivery", format_price(delivery_fee_for_order(order_details)))
    st.metric("Total", format_price(total_for_order(cart, order_details)))


def render_order_details(disabled: bool = False) -> OrderDetails:
    st.subheader("Datos del pedido")
    current_details = st.session_state.conversation_state.order_details

    customer_name = st.text_input("Nombre", value=current_details.customer_name, disabled=disabled)
    customer_phone = st.text_input("Telefono", value=current_details.customer_phone, disabled=disabled)
    fulfillment_label = st.radio(
        "Modalidad",
        options=("Delivery", "Recojo"),
        index=0 if current_details.fulfillment_type == "delivery" else 1,
        horizontal=True,
        disabled=disabled,
    )
    fulfillment_type = "delivery" if fulfillment_label == "Delivery" else "pickup"

    # Only retain the address or pickup store that applies to the currently selected fulfillment mode.
    delivery_address = ""
    pickup_store = ""
    if fulfillment_type == "delivery":
        delivery_address = st.text_input(
            "Direccion de delivery",
            value=current_details.delivery_address,
            disabled=disabled,
        )
    else:
        pickup_store = st.selectbox(
            "Tienda de recojo",
            options=PICKUP_STORES,
            index=_pickup_store_index(current_details.pickup_store),
            disabled=disabled,
        )

    requested_date = st.date_input(
        "Fecha solicitada",
        # An empty date means the customer has not selected one; the minimum remains a validation rule.
        value=current_details.requested_date,
        min_value=date.today(),
        disabled=disabled,
    )

    details = OrderDetails(
        customer_name=customer_name,
        customer_phone=customer_phone,
        fulfillment_type=fulfillment_type,
        requested_date=requested_date,
        delivery_address=delivery_address,
        pickup_store=pickup_store,
    )
    persist_conversation_state(replace(st.session_state.conversation_state, order_details=details))

    # Display domain validation without duplicating its rules in the form.
    validation = validate_order_details(details)
    if validation.is_valid:
        st.success("Los datos del pedido estan completos para esta etapa.")
    else:
        st.warning("Faltan datos o hay datos invalidos.")
        if validation.missing_fields:
            st.caption("Faltantes: " + ", ".join(validation.missing_fields))
        if validation.invalid_fields:
            st.caption("Invalidos: " + ", ".join(validation.invalid_fields))

    return details


def render_confirmation(order_details: OrderDetails) -> None:
    st.subheader("Confirmacion")
    state = st.session_state.conversation_state
    cart = state.cart
    validation = validate_order_details(order_details)
    # Confirmation is intentionally one-way in this MVP to prevent duplicate local orders.
    can_confirm = not cart.is_empty and validation.is_valid and state.confirmed_order is None

    if state.confirmed_order is not None:
        st.success("Pedido confirmado. Queda pendiente de pago y revision.")
        return

    if cart.is_empty:
        st.info("Agrega al menos un producto para confirmar.")
    elif not validation.is_valid:
        st.info("Completa los datos del pedido para habilitar la confirmacion.")

    if st.button("Confirmar pedido", disabled=not can_confirm):
        # Persistence remains a server-side operation; the internal ID is never displayed to the customer.
        persist_conversation_state(
            replace(
                state,
                confirmed_order=save_confirmed_order(DATABASE_PATH, cart, order_details),
            )
        )
        st.rerun()


def _pickup_store_index(pickup_store: str) -> int:
    if pickup_store in PICKUP_STORES:
        return PICKUP_STORES.index(pickup_store)
    return 0


def respond_to_chat_message(user_message: str) -> str:
    """Delegate one chat message; ConversationService persists the resulting state."""

    turn = st.session_state.conversation_service.handle_message(st.session_state.conversation_id, user_message)
    st.session_state.conversation_state = st.session_state.conversation_service.load_conversation(
        st.session_state.conversation_id
    )
    return turn.reply


def render_chat() -> None:
    """Render the primary ordering surface and keep its input close to the conversation."""

    st.subheader("Habla con Patty")
    st.caption("Dime qué necesitas y te ayudo a armar el pedido.")

    conversation = st.container(height=520, border=True)
    with conversation:
        if not st.session_state.conversation_state.messages:
            with st.chat_message("assistant"):
                st.write("¡Hola! Cuéntame qué productos buscas para tu pedido.")
        for message in st.session_state.conversation_state.messages:
            with st.chat_message(message.role):
                st.write(message.content)

    user_message = st.chat_input("Escribe un mensaje para Patty")
    if user_message:
        respond_to_chat_message(user_message)
        st.rerun()


def main() -> None:
    configure_application_logging()
    st.set_page_config(page_title=APP_TITLE)
    catalog = get_catalog()
    initialize_session_state(catalog)

    st.title(APP_TITLE)
    st.caption("Arma tu pedido conversando con Patty. Puedes revisar y confirmar los detalles a la derecha.")
    # Every editable area receives the same lock after a successful confirmation.
    order_confirmed = st.session_state.conversation_state.confirmed_order is not None

    chat_column, order_column = st.columns((7, 5), gap="large")
    with chat_column:
        render_chat()

        with st.expander("Buscar productos manualmente", expanded=False):
            st.write("Consulta el catálogo y agrega productos sin usar el chat.")
            catalog_query = st.text_input(
                "Buscar producto, alias o categoría",
                placeholder="Ej. red velvet",
            )
            render_catalog_result(search_products(catalog, catalog_query), catalog, disabled=order_confirmed)

    with order_column:
        st.subheader("Tu pedido")
        order_details = st.session_state.conversation_state.order_details
        render_cart(order_details, disabled=order_confirmed)
        st.divider()
        with st.expander("Datos de entrega", expanded=not order_confirmed):
            order_details = render_order_details(disabled=order_confirmed)
        st.divider()
        render_confirmation(order_details)


if __name__ == "__main__":
    main()
