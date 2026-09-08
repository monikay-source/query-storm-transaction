from decimal import Decimal

from .models import ProcessedTransaction


def _processed(transaction, customer, product, status, error=None):
    return ProcessedTransaction(
        transaction.id,
        transaction.customer_id,
        customer.get("name") if customer else None,
        transaction.product_id,
        product.get("name") if product else None,
        transaction.quantity,
        product.get("price")
        if product and product.get("price") is not None
        else transaction.unit_price,
        status,
        error,
    )


def process_transactions(database, transactions):
    results = []
    for transaction in transactions:
        customer = database.get_customer(transaction.customer_id)
        product = database.get_product(transaction.product_id)

        if customer is None:
            results.append(
                _processed(transaction, None, product, "failed", "customer_not_found")
            )
        elif not customer["is_active"]:
            results.append(
                _processed(transaction, customer, product, "failed", "customer_inactive")
            )
        elif product is None:
            results.append(
                _processed(transaction, customer, None, "failed", "product_not_found")
            )
        elif not product["is_available"]:
            results.append(
                _processed(
                    transaction, customer, product, "failed", "product_unavailable"
                )
            )
        else:
            results.append(_processed(transaction, customer, product, "completed"))
    return results


class TransferError(Exception):
    pass


def process_transfer(database, source_id, destination_id, amount):
    amount = Decimal(amount)
    if amount <= 0:
        raise TransferError("Amount must be positive")

    source = database.get_account(source_id)
    if source is None:
        raise TransferError("Source account not found")
    if source["balance"] < amount:
        raise TransferError("Insufficient funds")

    source["balance"] -= amount
    database.save_account(source)

    destination = database.get_account(destination_id)
    if destination is None:
        raise TransferError("Destination account not found")

    destination["balance"] += amount
    database.save_account(destination)
    return database.create_transfer(source_id, destination_id, amount)
