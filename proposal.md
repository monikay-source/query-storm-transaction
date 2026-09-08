Proposal

Task: ORM Performance Disaster — N+1 Query + Transaction Failure

Difficulty: Medium
Two backend failures in one service, with no ORM, no network and no real database:
1. Reading - The batch loop fetches a customer and a product for every row, so cost grows with the size of the batch instead of with the number of distinct records it mentions.
2. Writing - A transfer saves one balance and then fails, leaving the two accounts out of step.

Neither is a matter of taste. The in memory store counts its reads and holds the balances and the transfer history, so a fix is measurable.

Intended approach

Reads — ask first, fetch once - Note every record the batch needs, fetch each kind in one go, and answer every row from a small cache. Any batch size costs one read per record type, and an empty batch costs none. Repeated and missing references cost nothing extra. The cache lasts for one call only, so the read count is the same on every run instead of drifting as a longer lived cache fills up.

Writes — decide first, then write on a copy - Check the amount and both accounts, work out the final balances, and gather the writes. Then run those writes against copies of the account table and the transfer list, with the originals held aside. If anything fails, the originals go back. Because the originals are never modified, there is nothing to unwind and that holds even for a failure thrown inside the store's own write methods, which is the case that checking things in the right order cannot cover on its own.

Result shape, validation order, and behavior for empty, repeated, invalid and valid input all stay as they are. The public entry points, the models, the store and the evaluator are untouched; only the service changes.

How it's verified

The evaluator checks four things: transaction results and error codes, the read count for a large batch, balances and record creation after a good transfer, and balances and history after a failed one. The baseline passes the ordinary cases and fails the read-count and rollback checks, so leaving the service alone cannot pass. The golden `solve.sh` passes everything. The evaluator exits zero only on a full pass.

Category

Backend debugging and repair: data-access cost, atomic updates, validation order, and staying consistent when things fail.
