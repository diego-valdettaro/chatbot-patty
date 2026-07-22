import streamlit as st

from patty_bot.catalog import CatalogSearchResult, load_catalog, search_products
from patty_bot.config import APP_TITLE, CATALOG_SAMPLE_PATH


def initialize_session_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []


@st.cache_data
def get_catalog():
    return load_catalog(CATALOG_SAMPLE_PATH)


def format_price(value) -> str:
    return f"S/ {value:.2f}"


def render_catalog_result(result: CatalogSearchResult) -> None:
    if not result.query.strip():
        st.info("Escribe una busqueda para consultar el catalogo.")
        return

    if not result.found:
        st.warning("No encontramos ese producto en el catalogo sample de Patty.")
        return

    rows = [
        {
            "Producto": match.product.name,
            "Categoria": match.product.category,
            "Precio": format_price(match.product.price),
            "Coincidencia": match.match_type,
            "Score": round(match.score, 2),
        }
        for match in result.matches
    ]
    st.dataframe(rows, hide_index=True, use_container_width=True)


def main() -> None:
    st.set_page_config(page_title=APP_TITLE)
    initialize_session_state()

    st.title(APP_TITLE)
    st.caption("MVP local para construir y validar el flujo del chatbot de pedidos.")

    st.subheader("Busqueda de catalogo")
    st.write("Consulta productos reales del catalogo sample antes de conectarlos al carrito.")
    catalog = get_catalog()
    catalog_query = st.text_input("Buscar producto, alias o categoria", placeholder="Ej. red velbet")
    render_catalog_result(search_products(catalog, catalog_query))

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
