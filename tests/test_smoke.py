from patty_bot.config import APP_TITLE, DELIVERY_FEE, PICKUP_STORES


def test_base_configuration_is_available():
    assert APP_TITLE == "Chatbot de pedidos Patty"
    assert DELIVERY_FEE == 10
    assert PICKUP_STORES == ("Benavides", "San Isidro")
