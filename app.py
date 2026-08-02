from datetime import date

import streamlit as st

from patty_bot.agent_router import create_openai_client, run_agent_turn
from patty_bot.cart import Cart, add_product_to_cart, change_cart_item_quantity, remove_product_from_cart
from patty_bot.catalog import CatalogSearchResult, load_catalog, search_products
from patty_bot.config import (
    APP_TITLE,
    CATALOG_SAMPLE_PATH,
    DATABASE_PATH,
    LLMConfigurationError,
    PICKUP_STORES,
    load_llm_settings,
)
from patty_bot.orders import (
    OrderDetails,
    delivery_fee_for_order,
    minimum_requested_date,
    total_for_order,
    validate_order_details,
)
from patty_bot.repository import save_confirmed_order
from patty_bot.tool_executor import AgentSession


def initialize_session_state() -> None:
    # Session state is the UI-owned boundary until the agent executor replaces this temporary flow.
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "cart" not in st.session_state:
        st.session_state.cart = Cart()
    if "order_details" not in st.session_state:
        st.session_state.order_details = OrderDetails(requested_date=minimum_requested_date())
    if "confirmed_order" not in st.session_state:
        # Keep the complete aggregate in session after confirmation, not just a disconnected ID.
        st.session_state.confirmed_order = None
    if "agent_client" not in st.session_state:
        st.session_state.agent_client = None
    if "agent_client_key" not in st.session_state:
        st.session_state.agent_client_key = None


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
                st.session_state.cart = add_product_to_cart(st.session_state.cart, catalog, product.id)
                st.rerun()


def render_cart(order_details: OrderDetails, disabled: bool = False) -> None:
    st.subheader("Carrito")
    cart = st.session_state.cart

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
                st.session_state.cart = change_cart_item_quantity(cart, item.product.id, int(quantity))
                st.rerun()
        with columns[2]:
            st.write(format_price(item.line_subtotal))
        with columns[3]:
            if st.button("Quitar", key=f"remove-{item.product.id}", disabled=disabled):
                st.session_state.cart = remove_product_from_cart(cart, item.product.id)
                st.rerun()

    st.metric("Subtotal", format_price(cart.subtotal))
    st.metric("Delivery", format_price(delivery_fee_for_order(order_details)))
    st.metric("Total", format_price(total_for_order(cart, order_details)))


def render_order_details(disabled: bool = False) -> OrderDetails:
    st.subheader("Datos del pedido")
    current_details = st.session_state.order_details

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
        value=current_details.requested_date or minimum_requested_date(),
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
    st.session_state.order_details = details

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
    cart = st.session_state.cart
    validation = validate_order_details(order_details)
    # Confirmation is intentionally one-way in this MVP to prevent duplicate local orders.
    can_confirm = not cart.is_empty and validation.is_valid and st.session_state.confirmed_order is None

    if st.session_state.confirmed_order is not None:
        st.success("Pedido confirmado. Queda pendiente de pago y revision.")
        return

    if cart.is_empty:
        st.info("Agrega al menos un producto para confirmar.")
    elif not validation.is_valid:
        st.info("Completa los datos del pedido para habilitar la confirmacion.")

    if st.button("Confirmar pedido", disabled=not can_confirm):
        # Persistence remains a server-side operation; the internal ID is never displayed to the customer.
        st.session_state.confirmed_order = save_confirmed_order(DATABASE_PATH, cart, order_details)
        st.rerun()


def _pickup_store_index(pickup_store: str) -> int:
    if pickup_store in PICKUP_STORES:
        return PICKUP_STORES.index(pickup_store)
    return 0


def respond_to_chat_message(user_message: str, catalog, conversation) -> str:
    """Route one chat message through the LLM while keeping all order state in session."""

    try:
        settings = load_llm_settings()
    except LLMConfigurationError:
        return "El chat con Patty aun no esta configurado. Completa las variables del LLM para activarlo."

    # Cache the client in this Streamlit session without putting the API key in displayed state.
    if st.session_state.agent_client is None or st.session_state.agent_client_key != settings.api_key:
        try:
            st.session_state.agent_client = create_openai_client(settings)
            st.session_state.agent_client_key = settings.api_key
        except RuntimeError:
            return "Falta instalar la dependencia de OpenAI. Ejecuta la instalacion del proyecto nuevamente."

    agent_session = AgentSession(
        products=tuple(catalog),
        database_path=DATABASE_PATH,
        cart=st.session_state.cart,
        order_details=st.session_state.order_details,
        confirmed_order=st.session_state.confirmed_order,
    )
    try:
        turn = run_agent_turn(
            st.session_state.agent_client,
            settings,
            agent_session,
            user_message,
            conversation,
        )
    except Exception:
        # Do not render provider errors because they may reveal operational details to customers.
        return "No pude responder en este momento. Intenta nuevamente en unos instantes."

    st.session_state.cart = turn.session.cart
    st.session_state.order_details = turn.session.order_details
    st.session_state.confirmed_order = turn.session.confirmed_order
    return turn.reply


def render_chat(catalog) -> None:
    """Render the primary ordering surface and keep its input close to the conversation."""

    st.subheader("Habla con Patty")
    st.caption("Dime qué necesitas y te ayudo a armar el pedido.")

    conversation = st.container(height=520, border=True)
    with conversation:
        if not st.session_state.messages:
            with st.chat_message("assistant"):
                st.write("¡Hola! Cuéntame qué productos buscas para tu pedido.")
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])

    user_message = st.chat_input("Escribe un mensaje para Patty")
    if user_message:
        st.session_state.messages.append({"role": "user", "content": user_message})
        assistant_message = respond_to_chat_message(
            user_message,
            catalog,
            st.session_state.messages[:-1],
        )
        st.session_state.messages.append({"role": "assistant", "content": assistant_message})
        st.rerun()


def main() -> None:
    st.set_page_config(page_title=APP_TITLE)
    initialize_session_state()

    st.title(APP_TITLE)
    st.caption("Arma tu pedido conversando con Patty. Puedes revisar y confirmar los detalles a la derecha.")
    # Every editable area receives the same lock after a successful confirmation.
    order_confirmed = st.session_state.confirmed_order is not None
    catalog = get_catalog()

    chat_column, order_column = st.columns((7, 5), gap="large")
    with chat_column:
        render_chat(catalog)

        with st.expander("Buscar productos manualmente", expanded=False):
            st.write("Consulta el catálogo y agrega productos sin usar el chat.")
            catalog_query = st.text_input(
                "Buscar producto, alias o categoría",
                placeholder="Ej. red velvet",
            )
            render_catalog_result(search_products(catalog, catalog_query), catalog, disabled=order_confirmed)

    with order_column:
        st.subheader("Tu pedido")
        order_details = st.session_state.order_details
        render_cart(order_details, disabled=order_confirmed)
        st.divider()
        with st.expander("Datos de entrega", expanded=not order_confirmed):
            order_details = render_order_details(disabled=order_confirmed)
        st.divider()
        render_confirmation(order_details)


if __name__ == "__main__":
    main()
