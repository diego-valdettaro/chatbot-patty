from datetime import date

import streamlit as st

from patty_bot.cart import Cart, add_product_to_cart, change_cart_item_quantity, remove_product_from_cart
from patty_bot.catalog import CatalogSearchResult, load_catalog, search_products
from patty_bot.config import APP_TITLE, CATALOG_SAMPLE_PATH, DATABASE_PATH, PICKUP_STORES
from patty_bot.orders import (
    OrderDetails,
    delivery_fee_for_order,
    minimum_requested_date,
    total_for_order,
    validate_order_details,
)
from patty_bot.repository import save_confirmed_order


def initialize_session_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "cart" not in st.session_state:
        st.session_state.cart = Cart()
    if "order_details" not in st.session_state:
        st.session_state.order_details = OrderDetails(requested_date=minimum_requested_date())
    if "order_confirmed" not in st.session_state:
        st.session_state.order_confirmed = False
    if "confirmed_order_id" not in st.session_state:
        st.session_state.confirmed_order_id = None


@st.cache_data
def get_catalog():
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
    can_confirm = not cart.is_empty and validation.is_valid and not st.session_state.order_confirmed

    if st.session_state.order_confirmed:
        st.success("Pedido confirmado. Queda pendiente de pago y revision.")
        return

    if cart.is_empty:
        st.info("Agrega al menos un producto para confirmar.")
    elif not validation.is_valid:
        st.info("Completa los datos del pedido para habilitar la confirmacion.")

    if st.button("Confirmar pedido", disabled=not can_confirm):
        order_id = save_confirmed_order(DATABASE_PATH, cart, order_details)
        st.session_state.order_confirmed = True
        st.session_state.confirmed_order_id = order_id
        st.rerun()


def _pickup_store_index(pickup_store: str) -> int:
    if pickup_store in PICKUP_STORES:
        return PICKUP_STORES.index(pickup_store)
    return 0


def main() -> None:
    st.set_page_config(page_title=APP_TITLE)
    initialize_session_state()

    st.title(APP_TITLE)
    st.caption("MVP local para construir y validar el flujo del chatbot de pedidos.")
    order_confirmed = st.session_state.order_confirmed

    st.subheader("Busqueda de catalogo")
    st.write("Consulta productos reales del catalogo sample y agregalos al carrito.")
    catalog = get_catalog()
    catalog_query = st.text_input("Buscar producto, alias o categoria", placeholder="Ej. red velbet")
    render_catalog_result(search_products(catalog, catalog_query), catalog, disabled=order_confirmed)

    st.divider()

    order_details = render_order_details(disabled=order_confirmed)

    st.divider()

    render_cart(order_details, disabled=order_confirmed)

    st.divider()

    render_confirmation(order_details)

    st.divider()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    user_message = st.chat_input("Escribe un mensaje para Patty")
    if user_message:
        st.session_state.messages.append({"role": "user", "content": user_message})
        assistant_message = (
            "Todavia estoy en construccion. En esta etapa solo validamos que la app local arranque."
        )
        st.session_state.messages.append({"role": "assistant", "content": assistant_message})
        st.rerun()


if __name__ == "__main__":
    main()
