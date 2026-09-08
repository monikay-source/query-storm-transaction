from decimal import Decimal


class Account:
    def __init__(self, account_id, owner, balance):
        self.id = account_id
        self.owner = owner
        self.balance = Decimal(balance)


class Transfer:
    def __init__(self, transfer_id, source_id, destination_id, amount):
        self.id = transfer_id
        self.source_id = source_id
        self.destination_id = destination_id
        self.amount = Decimal(amount)


class Transaction:
    def __init__(self, transaction_id, customer_id, product_id, quantity, unit_price):
        self.id = transaction_id
        self.customer_id = customer_id
        self.product_id = product_id
        self.quantity = quantity
        self.unit_price = Decimal(unit_price)

    @property
    def total_amount(self):
        return self.unit_price * self.quantity

    def to_dict(self):
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "product_id": self.product_id,
            "quantity": self.quantity,
            "unit_price": str(self.unit_price),
            "total_amount": str(self.total_amount),
        }


class ProcessedTransaction:
    def __init__(
        self,
        transaction_id,
        customer_id,
        customer_name,
        product_id,
        product_name,
        quantity,
        unit_price,
        status,
        error=None,
    ):
        self.transaction_id = transaction_id
        self.customer_id = customer_id
        self.customer_name = customer_name
        self.product_id = product_id
        self.product_name = product_name
        self.quantity = quantity
        self.unit_price = Decimal(unit_price)
        self.status = status
        self.error = error

    @property
    def total_amount(self):
        return self.unit_price * self.quantity

    def to_dict(self):
        return {
            "transaction_id": self.transaction_id,
            "customer_id": self.customer_id,
            "customer_name": self.customer_name,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "quantity": self.quantity,
            "unit_price": str(self.unit_price),
            "total_amount": str(self.total_amount),
            "status": self.status,
            "error": self.error,
        }
