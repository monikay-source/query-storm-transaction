ORM Performance Disaster: N+1 Query + Transaction Failure

A self-contained Terminal-Bench task: an in-memory store, two backend bugs, no ORM and no network.

- Too many reads — the batch loop fetches a customer and a product for every row.
- Half-finished transfers — a transfer can save one balance and then fail.

The baseline in `src/` handles ordinary cases correctly and fails the read-count and rollback checks on purpose.

What's in the bundle

instruction.md - The task as the agent sees it. Says what to achieve, not how. 
Dockerfile - Debian-based testbed with the broken service inside. 
solve.sh - The golden fix. Deterministic, no prompts. 
eval.py  - The verifier. Pass or fail, exit 0 only on a full pass. 
tests/ - Pytest suite: behavior, read count, transfer atomicity. 
src/ - The service being repaired. 
proposal.md , README.md - Notes for reviewers. Kept out of the Docker image so they don't give the answer away. 

How to check it

The baseline must fail:

```bash
pytest && python eval.py
```

The golden fix must pass:

```bash
bash solve.sh && pytest && python eval.py
```

`solve.sh` overwrites the broken service, so on its first run it saves a copy of `src/` into `.baseline/`. To break the tree again and repeat the check:

```bash
bash solve.sh --reset
```

The copy is only taken on the first run, so re-applying the fix never saves an already fixed tree. `.baseline/` is made at run time and isn't part of the bundle.

In Docker:

```bash
docker build -t orm-disaster .
docker run --rm orm-disaster eval.py
docker run --rm --entrypoint bash orm-disaster -c "bash solve.sh && python -m pytest -q && python eval.py"
```

What to expect
Baseline - 3 failed, 10 passed , `EVALUATION: FAIL`, exit 1 
After - solve.sh - 13 passed , `EVALUATION: PASS`, exit 0 

The three baseline failures are `test_large_batch_query_efficiency`, `test_many_unique_records_query_count`, and `test_missing_destination_rolls_back_source_and_transfer_history`.

How the fix works

Written up here for reviewers. `solve.sh` applies it; none of it is in the baseline tree.

Reads — ask first, fetch once. `src/repository.py` splits asking for a record from reading it. The service walks the batch once to note every record it needs, then walks it again to use them, and that second pass triggers one bulk read per record type. Any batch size costs 2 reads, and an empty batch costs 0. A record is only ever asked for once, so repeated references are free and a missing one is never looked up twice. The cache is thrown away when the call ends, so the count never depends on what an earlier call left behind.

Writes — decide first, then write on a copy. Three steps:

1. `src/transfer_plan.py` checks the amount and both accounts and works out the final balances. It writes nothing. Balances are recorded as final amounts rather than as plus-and-minus changes, so a transfer from an account to itself comes out even instead of being counted twice.
2. `src/write_set.py` gathers the writes, then checks each account still holds the balance the plan was based on. If the store has moved on since, the commit is refused before anything happens.
3. The writes then run against copies of the account table and the transfer list, with the originals held aside. If anything raises, the originals go straight back.

Since the originals are never modified, a failure has nothing to unwind — not even a failure thrown by `save_account` or `create_transfer`, which is the case that checking things in the right order misses. The cost is one shallow copy of the account table per transfer; only the accounts taking part get copied properly.

Two things worth knowing: after a transfer the accounts involved are new objects, so read them back with `database.get_account` rather than holding on to a record across the call; and a bad amount (non-numeric, `None`, `NaN`, infinite, zero or negative) raises `TransferError` instead of leaking a `decimal` error.

Determinism

No network, no clock, no randomness, and no results that depend on dict ordering. `eval.py` runs three independent checks and exits 0 or 1.
