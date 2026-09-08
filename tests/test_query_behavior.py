from decimal import Decimal

from src.app import process_and_serialize
from src.database import Customer, Database, Product
from src.models import Transaction


def large_database():
    database = Database()
    database.load_customers([Customer(i, "Customer %s" % i) for i in range(1, 101)])
    database.load_products([Product(i, "Product %s" % i, Decimal("1.00")) for i in range(1, 51)])
    return database


def test_small_batch_query_count():
    database = large_database()
    transactions = [Transaction(str(i), (i % 2) + 1, (i % 2) + 1, 1, "1") for i in range(5)]
    database.reset_query_count()
    assert len(process_and_serialize(database, transactions)) == 5
    assert database.get_query_count() <= 20


def test_large_batch_query_efficiency():
    database = large_database()
    transactions = [Transaction(str(i), (i % 10) + 1, (i % 5) + 1, 1, "1") for i in range(500)]
    database.reset_query_count()
    assert len(process_and_serialize(database, transactions)) == 500
    assert database.get_query_count() <= 100


def test_many_unique_records_query_count():
    database = large_database()
    transactions = [Transaction(str(i), i, (i % 5) + 1, 1, "1") for i in range(1, 101)]
    database.reset_query_count()
    assert len(process_and_serialize(database, transactions)) == 100
    assert database.get_query_count() <= 50


def test_query_count_determinism():
    database = large_database()
    transactions = [Transaction(str(i), (i % 10) + 1, (i % 5) + 1, 1, "1") for i in range(30)]
    counts = []
    for _ in range(2):
        database.reset_query_count()
        process_and_serialize(database, transactions)
        counts.append(database.get_query_count())
    assert counts[0] == counts[1]
