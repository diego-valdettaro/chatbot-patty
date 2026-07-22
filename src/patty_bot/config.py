from pathlib import Path


APP_TITLE = "Chatbot de pedidos Patty"

DELIVERY_FEE = 10

PICKUP_STORES = ("Benavides", "San Isidro")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CATALOG_SAMPLE_PATH = PROJECT_ROOT / "data" / "catalog.sample.csv"
