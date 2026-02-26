import asyncio
from app.services.catalog_data_collector import CatalogDataCollector

def test():
    collector = CatalogDataCollector()
    res = collector._fetch_supply_data("005930") # Samsung Electronics
    print(res)

if __name__ == "__main__":
    test()
