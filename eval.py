from decimal import Decimal
import sys

from src.app import process_and_serialize
from src.app import transfer_and_serialize
from src.database import Customer, Database, Product
from src.models import Account
from src.models import Transaction


def make_database():
    database = Database()
    database.load_customers([Customer(i, "Customer %s" % i) for i in range(1, 101)])
    database.load_products([Product(i, "Product %s" % i, Decimal("1.00")) for i in range(1, 51)])
    return database


def functional_check():
    database = make_database()
    transactions = [
        Transaction("valid", 1, 1, 2, "1.00"),
        Transaction("missing", 999, 1, 1, "1.00"),
        Transaction("missing-product", 1, 999, 1, "1.00"),
    ]
    result = process_and_serialize(database, transactions)
    return (
        len(result) == 3
        and result[0]["status"] == "completed"
        and result[1]["error"] == "customer_not_found"
        and result[2]["error"] == "product_not_found"
    )


def efficiency_check():
    database = make_database()
    transactions = [
        Transaction(str(i), (i % 10) + 1, (i % 5) + 1, 1, "1.00")
        for i in range(500)
    ]
    database.reset_query_count()
    result = process_and_serialize(database, transactions)
    return len(result) == 500 and database.get_query_count() <= 100


def transfer_check():
    database = Database()
    database.load_accounts(
        [Account(1, "monika", "100.00"), Account(2, "ela", "50.00")]
    )
    transfer_and_serialize(database, 1, 2, "25.00")
    success = (
        database.get_account(1)["balance"] == Decimal("75.00")
        and database.get_account(2)["balance"] == Decimal("75.00")
        and len(database.transfers) == 1
    )

    database.load_accounts([Account(3, "jeevi", "100.00")])
    try:
        transfer_and_serialize(database, 3, 999, "25.00")
    except Exception:
        pass
    else:
        return False
    rollback = (
        database.get_account(3)["balance"] == Decimal("100.00")
        and len(database.transfers) == 1
    )
    return success and rollback


def main():
    functional = functional_check()
    efficient = efficiency_check()
    transfers = transfer_check()
    print("Functional checks: %s" % ("PASS" if functional else "FAIL"))
    print("Query efficiency: %s" % ("PASS" if efficient else "FAIL"))
    print("Transfer atomicity: %s" % ("PASS" if transfers else "FAIL"))
    passed = functional and efficient and transfers
    print("EVALUATION: %s" % ("PASS" if passed else "FAIL"))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
