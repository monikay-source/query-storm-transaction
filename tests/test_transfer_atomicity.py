from decimal import Decimal

import pytest

from src.app import transfer_and_serialize
from src.database import Database
from src.models import Account
from src.transaction_service import TransferError


def make_database():
    database = Database()
    database.load_accounts(
        [Account(1, "Alice", "100.00"), Account(2, "Bob", "50.00")]
    )
    return database


def test_successful_transfer_updates_both_accounts_and_records():
    database = make_database()

    transfer = transfer_and_serialize(database, 1, 2, "25.00")

    assert transfer["source_id"] == 1
    assert database.get_account(1)["balance"] == Decimal("75.00")
    assert database.get_account(2)["balance"] == Decimal("75.00")
    assert len(database.transfers) == 1


def test_missing_destination_rolls_back_source_and_transfer_history():
    database = make_database()

    with pytest.raises(TransferError):
        transfer_and_serialize(database, 1, 999, "25.00")

    assert database.get_account(1)["balance"] == Decimal("100.00")
    assert database.get_account(2)["balance"] == Decimal("50.00")
    assert database.transfers == []
