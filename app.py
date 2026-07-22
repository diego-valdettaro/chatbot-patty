import streamlit as st

from patty_bot.cart import Cart, add_product_to_cart, change_cart_item_quantity, remove_product_from_cart
from patty_bot.catalog import CatalogSearchResult, load_catalog, search_products
from patty_bot.config import APP_TITLE, CATALOG_SAMPLE_PATH


def initialize_session_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "cart" not in st.session_state:
        st.session_state.cart = Cart()


@st.cache_data
def get_catalog():
    return load_catalog(CATALOG_SAMPLE_PATH)


def format_price(value) -> str:
    return f"S/ {value:.2f}"


def render_catalog_result(result: CatalogSearchResult, catalog) -> None:
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
            st.caption(f"{product.category} · {match.match_type} · score {match.score:.2f}")
        with columns[1]:
            st.write(format_price(product.price))
        with columns[2]:
            if st.button("Agregar", key=f"add-{product.id}"):
                st.session_state.cart = add_product_to_cart(st.session_state.cart, catalog, product.id)
                st.rerun()


def render_cart() -> None:
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
                key=f"quantity-{item.product.id}",
            )
            if quantity != item.quantity:
                st.session_state.cart = change_cart_item_quantity(cart, item.product.id, int(quantity))
                st.rerun()
        with columns[2]:
            st.write(format_price(item.line_subtotal))
        with columns[3]:
            if st.button("Quitar", key=f"remove-{item.product.id}"):
                st.session_state.cart = remove_product_from_cart(cart, item.product.id)
                st.rerun()

    st.metric("Subtotal", format_price(cart.subtotal))
    st.metric("Delivery", format_price(cart.delivery_fee))
    st.metric("Total", format_price(cart.total))


def main() -> None:
    st.set_page_config(page_title=APP_TITLE)
    initialize_session_state()

    st.title(APP_TITLE)
    st.caption("MVP local para construir y validar el flujo del chatbot de pedidos.")

    st.subheader("Busqueda de catalogo")
    st.write("Consulta productos reales del catalogo sample y agregalos al carrito.")
    catalog = get_catalog()
    catalog_query = st.text_input("Buscar producto, alias o categoria", placeholder="Ej. red velbet")
    render_catalog_result(search_products(catalog, catalog_query), catalog)

    st.divider()

    render_cart()

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
