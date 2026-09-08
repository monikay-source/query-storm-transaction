from decimal import Decimal

import pytest

from src.app import process_and_serialize
from src.database import Customer, Database, Product
from src.models import Transaction


@pytest.fixture
def database_with_data():
    database = Database()
    database.load_customers(
        [Customer(1, "Alice"), Customer(2, "Bob"), Customer(3, "Inactive", False)]
    )
    database.load_products(
        [
            Product(1, "Widget", Decimal("10.00")),
            Product(2, "Gadget", Decimal("20.00")),
            Product(3, "Unavailable", Decimal("30.00"), False),
        ]
    )
    return database


def test_empty_transaction_list(database_with_data):
    assert process_and_serialize(database_with_data, []) == []


def test_single_transaction_success(database_with_data):
    result = process_and_serialize(
        database_with_data, [Transaction("T1", 1, 1, 2, "10.00")]
    )
    assert result[0]["status"] == "completed"
    assert result[0]["customer_name"] == "Alice"
    assert result[0]["product_name"] == "Widget"


def test_multiple_transactions_mixed_valid_invalid(database_with_data):
    transactions = [
        Transaction("T1", 1, 1, 1, "10"),
        Transaction("T2", 99, 1, 1, "10"),
        Transaction("T3", 1, 99, 1, "10"),
    ]
    result = process_and_serialize(database_with_data, transactions)
    assert [item["status"] for item in result] == ["completed", "failed", "failed"]
    assert [item["error"] for item in result] == [None, "customer_not_found", "product_not_found"]


def test_inactive_customer(database_with_data):
    result = process_and_serialize(
        database_with_data, [Transaction("T1", 3, 1, 1, "10")]
    )
    assert result[0]["status"] == "failed"
    assert result[0]["error"] == "customer_inactive"


def test_unavailable_product(database_with_data):
    result = process_and_serialize(
        database_with_data, [Transaction("T1", 1, 3, 1, "10")]
    )
    assert result[0]["status"] == "failed"
    assert result[0]["error"] == "product_unavailable"


def test_duplicate_references(database_with_data):
    transactions = [Transaction(str(i), 1, 1, i, "10") for i in range(1, 6)]
    result = process_and_serialize(database_with_data, transactions)
    assert len(result) == 5
    assert all(item["status"] == "completed" for item in result)


def test_many_transactions(database_with_data):
    transactions = [Transaction(str(i), (i % 2) + 1, (i % 2) + 1, 1, "10") for i in range(100)]
    result = process_and_serialize(database_with_data, transactions)
    assert len(result) == 100
    assert all(item["status"] == "completed" for item in result)
