import threading
from dataclasses import dataclass
from decimal import Decimal


class QueryTracker:
    def __init__(self):
        self._local = threading.local()

    def reset(self):
        self._local.count = 0

    def increment(self):
        self._local.count = getattr(self._local, "count", 0) + 1

    def count(self):
        return getattr(self._local, "count", 0)


@dataclass
class Customer:
    id: int
    name: str
    is_active: bool = True


@dataclass
class Product:
    id: int
    name: str
    price: Decimal
    is_available: bool = True


class Database:
    def __init__(self):
        self.customers = {}
        self.products = {}
        self.accounts = {}
        self.transfers = []
        self.query_tracker = QueryTracker()

    def load_customers(self, customers):
        self.customers = {
            (item["id"] if isinstance(item, dict) else item.id): item
            for item in customers
        }

    def load_products(self, products):
        self.products = {
            (item["id"] if isinstance(item, dict) else item.id): item
            for item in products
        }

    def load_accounts(self, accounts):
        self.accounts = {
            (item["id"] if isinstance(item, dict) else item.id): item
            for item in accounts
        }

    def get_account(self, account_id):
        value = self.accounts.get(account_id)
        if value is None:
            return None
        if isinstance(value, dict):
            return value
        return {"id": value.id, "owner": value.owner, "balance": value.balance}

    def save_account(self, account):
        value = self.accounts[account["id"]]
        if isinstance(value, dict):
            value["balance"] = account["balance"]
        else:
            value.balance = account["balance"]

    def create_transfer(self, source_id, destination_id, amount):
        transfer = {
            "id": len(self.transfers) + 1,
            "source_id": source_id,
            "destination_id": destination_id,
            "amount": Decimal(amount),
        }
        self.transfers.append(transfer)
        return transfer

    @staticmethod
    def _record(value):
        if isinstance(value, dict):
            return value
        if isinstance(value, Customer):
            return {"id": value.id, "name": value.name, "is_active": value.is_active}
        return {
            "id": value.id,
            "name": value.name,
            "price": value.price,
            "is_available": value.is_available,
        }

    def get_customer(self, customer_id):
        self.query_tracker.increment()
        value = self.customers.get(customer_id)
        return self._record(value) if value is not None else None

    def get_customers_bulk(self, customer_ids):
        self.query_tracker.increment()
        return [
            self._record(self.customers[item])
            for item in customer_ids
            if item in self.customers
        ]

    def get_product(self, product_id):
        self.query_tracker.increment()
        value = self.products.get(product_id)
        return self._record(value) if value is not None else None

    def get_products_bulk(self, product_ids):
        self.query_tracker.increment()
        return [
            self._record(self.products[item])
            for item in product_ids
            if item in self.products
        ]

    def get_query_count(self):
        return self.query_tracker.count()

    def reset_query_count(self):
        self.query_tracker.reset()


def get_query_count(database):
    return database.get_query_count()


def reset_query_count(database):
    database.reset_query_count()
