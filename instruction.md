Task: ORM Performance Disaster — N+1 Query + Transaction Failure

The service in `src/` handles transaction batches and moves money between accounts, using the in memory store in `src/database.py`. It works on simple cases but breaks under load and under failure. Fix both problems.

Keep these signatures as they are:

- `src.app.process_and_serialize(database, transactions)` — returns one dict per input transaction. Keep the existing keys, the validation order, and the error codes exactly.
- `src.app.transfer_and_serialize(database, source_id, destination_id, amount)` — moves money between two accounts and returns the transfer record.

**Problem 1: too many reads.** The service reads the store once per row, so a large batch costs hundreds of reads even when it only refers to a handful of records. A batch of 500 transactions mentioning 10 customers and 5 products must not cost hundreds of reads. `src/database.py` already gives you what you need — use it, don't change it. The same input must cost the same number of reads on every run.

**Problem 2: half-finished transfers.** A transfer can save one account's new balance and then fail, so money vanishes or appears out of nowhere. Transfers must be all-or-nothing. One that works updates both balances and adds exactly one record. One that fails leaves every balance and the whole transfer history untouched. This must hold whether the failure comes from a validation check or from a write that fails halfway through.

Keep all of this working: empty batches, missing customers, missing products, inactive customers, unavailable products, repeated references in one batch, batches passed as any iterable, not enough money, zero and negative and non-numeric amounts, missing accounts, and accounts stored either as objects or as plain dicts.

Don't change the tests or the evaluator. Run `pytest`, then `python eval.py`. When you are done the evaluator must print `EVALUATION: PASS` and exit zero.
