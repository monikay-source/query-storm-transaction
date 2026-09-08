from .transaction_service import process_transactions
from .transaction_service import process_transfer


def process_and_serialize(database, transactions):
    processed = process_transactions(database, transactions)
    return [item.to_dict() for item in processed]


def transfer_and_serialize(database, source_id, destination_id, amount):
    return process_transfer(database, source_id, destination_id, amount)
