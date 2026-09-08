#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

BASELINE_DIR=".baseline"

clear_bytecode() {
    find . -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
}


if [ "${1:-}" = "--reset" ]; then
    if [ ! -d "$BASELINE_DIR/src" ]; then
        echo "No baseline snapshot found: solve.sh has not been run here." >&2
        exit 1
    fi
    rm -rf src
    cp -r "$BASELINE_DIR/src" src
    clear_bytecode
    echo "=== BASELINE RESTORED ==="
    exit 0
fi

if [ ! -d "$BASELINE_DIR/src" ]; then
    mkdir -p "$BASELINE_DIR"
    cp -r src "$BASELINE_DIR/src"
    rm -rf "$BASELINE_DIR/src/__pycache__"
fi

echo "=== APPLYING GOLDEN SOLUTION ==="

cat > src/repository.py <<'PYEOF'

class IdentityMap:
   
    def __init__(self, key_field="id"):
        self._key_field = key_field
        self._records = {}

    def add_all(self, records):
       
        for record in records:
            if isinstance(record, dict):
                key = record.get(self._key_field)
            else:
                key = getattr(record, self._key_field, None)
            if key is not None:
                self._records[key] = record

    def get(self, key):
       return self._records.get(key)


class BatchingRepository:
    
    def __init__(self, bulk_reader, key_field="id"):
        self._bulk_reader = bulk_reader
        self._identity_map = IdentityMap(key_field)
        self._queued = {}
        self._requested = set()

    def request(self, key):
       
        if key is None or key in self._requested:
            return
        self._queued[key] = None
        self._requested.add(key)

    def get(self, key):
        self.flush()
        return self._identity_map.get(key)

    def flush(self):
        
        if not self._queued:
            return
        keys = list(self._queued)
        self._queued.clear()
        self._identity_map.add_all(self._bulk_reader(keys))


class RecordSession:
   
    def __init__(self, database):
        self.customers = BatchingRepository(database.get_customers_bulk)
        self.products = BatchingRepository(database.get_products_bulk)

    def request(self, customer_id, product_id):
        self.customers.request(customer_id)
        self.products.request(product_id)

    def resolve(self, customer_id, product_id):
        return self.customers.get(customer_id), self.products.get(product_id)
PYEOF

# The baseline id-collection helpers are superseded by the repository above.
rm -f src/query.py

# --- write path ------------------------------------------------------------
cat > src/errors.py <<'PYEOF'

class TransferError(Exception):
    pass
    
class StaleWriteError(TransferError):
    pass
PYEOF

cat > src/transfer_plan.py <<'PYEOF'

from .errors import TransferError

class TransferPlan:
    __slots__ = ("source_id", "destination_id", "amount", "expected", "targets")

    def __init__(self, source_id, destination_id, amount, expected, targets):
        self.source_id = source_id
        self.destination_id = destination_id
        self.amount = amount
        self.expected = expected
        self.targets = targets

    def balance_writes(self):
        for account_id, target in self.targets.items():
            yield account_id, self.expected[account_id], target


def plan_transfer(source, destination, amount):
    if source["balance"] < amount:
        raise TransferError("Insufficient funds")

    expected = {}
    targets = {}
    for account, delta in ((source, -amount), (destination, amount)):
        account_id = account["id"]
        if account_id not in expected:
            expected[account_id] = account["balance"]
            targets[account_id] = account["balance"]
        targets[account_id] += delta

    return TransferPlan(source["id"], destination["id"], amount, expected, targets)
PYEOF

cat > src/write_set.py <<'PYEOF'
import copy

from .errors import StaleWriteError


def _detach(value):
    if isinstance(value, dict):
        return dict(value)
    return copy.copy(value)


class WriteSet:
    
    def __init__(self):
        self._balances = []
        self._transfer = None

    def stage_balance(self, account_id, expected, target):
        self._balances.append((account_id, expected, target))

    def stage_transfer(self, source_id, destination_id, amount):
        self._transfer = (source_id, destination_id, amount)

    def commit(self, database):
        self._verify(database)
        staged_accounts, staged_transfers = self._detached_state(database)

        live_accounts = database.accounts
        live_transfers = database.transfers
        database.accounts = staged_accounts
        database.transfers = staged_transfers
        try:
            for account_id, _expected, target in self._balances:
                database.save_account({"id": account_id, "balance": target})
            if self._transfer is None:
                return None
            return database.create_transfer(*self._transfer)
        except BaseException:
            database.accounts = live_accounts
            database.transfers = live_transfers
            raise

    def _verify(self, database):
        for account_id, expected, _target in self._balances:
            current = database.get_account(account_id)
            if current is None:
                raise StaleWriteError("Account %r no longer exists" % (account_id,))
            if current["balance"] != expected:
                raise StaleWriteError(
                    "Account %r changed since the transfer was planned" % (account_id,)
                )

    def _detached_state(self, database):
        accounts = dict(database.accounts)
        for account_id, _expected, _target in self._balances:
            accounts[account_id] = _detach(accounts[account_id])
        return accounts, list(database.transfers)
PYEOF

cat > src/transaction_service.py <<'PYEOF'
from decimal import Decimal, DecimalException

from .errors import StaleWriteError, TransferError
from .models import ProcessedTransaction
from .repository import RecordSession
from .transfer_plan import plan_transfer
from .write_set import WriteSet

__all__ = ["process_transactions", "process_transfer", "TransferError"]

# Field defaults mirror the Customer/Product dataclass defaults, so a record
# supplied as a plain dict without the flag behaves like one built from the
# model rather than raising.
ACTIVE_BY_DEFAULT = True
AVAILABLE_BY_DEFAULT = True


def _validation_error(customer, product):
    if customer is None:
        return "customer_not_found"
    if not customer.get("is_active", ACTIVE_BY_DEFAULT):
        return "customer_inactive"
    if product is None:
        return "product_not_found"
    if not product.get("is_available", AVAILABLE_BY_DEFAULT):
        return "product_unavailable"
    return None


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
    batch = list(transactions)
    session = RecordSession(database)

    for transaction in batch:
        session.request(transaction.customer_id, transaction.product_id)

    results = []
    for transaction in batch:
        customer, product = session.resolve(
            transaction.customer_id, transaction.product_id
        )
        error = _validation_error(customer, product)
        status = "failed" if error else "completed"
        results.append(_processed(transaction, customer, product, status, error))
    return results


def _coerce_amount(amount):
    try:
        value = Decimal(amount)
    except (DecimalException, TypeError, ValueError):
        raise TransferError("Amount is not a valid decimal") from None
    if not value.is_finite():
        raise TransferError("Amount is not a valid decimal")
    if value <= 0:
        raise TransferError("Amount must be positive")
    return value


def process_transfer(database, source_id, destination_id, amount):
    amount = _coerce_amount(amount)

    source = database.get_account(source_id)
    if source is None:
        raise TransferError("Source account not found")
    destination = database.get_account(destination_id)
    if destination is None:
        raise TransferError("Destination account not found")

    plan = plan_transfer(source, destination, amount)

    write_set = WriteSet()
    for account_id, expected, target in plan.balance_writes():
        write_set.stage_balance(account_id, expected, target)
    write_set.stage_transfer(plan.source_id, plan.destination_id, plan.amount)

    return write_set.commit(database)
PYEOF

clear_bytecode

echo "=== GOLDEN SOLUTION APPLIED ==="
