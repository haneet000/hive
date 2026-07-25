# Senior Engineer Review Prompt — Hive Take-Home (Final Pass)

Paste this into Claude Code inside your project root (where `app/`, `scripts/`,
`tests/`, `frontend/`, `alembic/` etc. already exist). Goal: an honest,
critical senior-engineer-style review before submission — not a rubber stamp.

---

## Role

Act as a senior backend engineer doing a pre-submission review of this
take-home, the way a hiring team lead actually would: read the code, run it,
verify the claims in the README against what the code actually does, and flag
anything that's inconsistent, hand-wavy, or would raise a question in a live
walkthrough. Don't just confirm things look fine — actively try to break it.

## 1. Verify the ₹5,741 revenue discrepancy

The dashboard's top-level "Total Gross Revenue" card shows ₹6,73,717, but
summing the "Total Revenue" column on the City AOV tab gives ₹6,67,976 — a
₹5,741 gap.

- Find the `/revenue` (or wherever gross revenue is computed) query and the
  `/stats/aov-by-city` query. Compare them line by line.
- Confirm (or disprove) the hypothesis: orders with `customer_id = NULL`
  (the 5 orphaned-customer orders) are included in the gross total but
  excluded from the by-city breakdown because they have no city to group by.
- Actually compute it: sum `total_amount` for completed orders where
  `customer_id IS NULL` and check if it equals ₹5,741 (or close, depending on
  how many of the 5 orphans are `completed` vs `refunded`/`cancelled`).
- If the numbers don't reconcile exactly, that's a real bug — find it (off-by-one
  in date range filters, a status filter mismatch between the two endpoints,
  double-counting from the duplicate-order dedup not being applied identically
  in both queries, etc.) rather than assuming the orphan-order theory is correct.
- Once confirmed, add one sentence to the README explaining the gap so it's
  not a silent surprise in review.

## 2. Verify the 108 vs 120 customer denominator

Ingestion reports 120 customers loaded, but the repeat-purchase-rate card
shows a denominator of 108. Confirm what population that 108 represents
(customers with ≥1 completed order? ≥1 order of any status? something else)
and check the code matches what the README claims. If the README doesn't
currently explain this, add a line.

## 3. Re-verify every claimed number end to end

Don't trust the last verification run — redo it fresh:

- Run `python -m scripts.ingest` **twice in a row** and diff the row counts
  (`customers`, `orders`, `order_items`, `ingestion_rejects`) between the two
  runs. They should be identical. If they're not, idempotency is broken —
  find out why (is it truncate-then-reload, or upsert? which did you actually
  build?).
- Run `pytest -v` and read every test name and assertion, not just the
  pass/fail count — are the assertions actually checking meaningful things,
  or just that no exception was raised?
- Manually recompute one endpoint's number from raw `data/orders.json` with a
  throwaway script, independent of your ingestion pipeline, and confirm it
  matches what the API returns. Pick `/stats/repeat-purchase-rate` or
  `/stats/aov-by-city` — whichever has more moving parts.
- Check whether `total_amount` is used directly for revenue math, or whether
  it's recomputed from `order_items` — if both exist, are they ever
  inconsistent for any order in the dataset? Check refunds specifically,
  since their sign convention is the trickiest part of this dataset.

## 4. Code review — things a senior reviewer actually checks

- **Dedup logic**: does "keep latest `order_date`" actually run *before*
  computing revenue/stats, or is there any code path where a stale duplicate
  could leak into an aggregate? Check for it explicitly with a query that
  counts distinct `order_id`s in whatever table/view feeds the endpoints.
- **N+1 queries**: does `/customers/{id}/orders` or `/customers/top` issue a
  query per row instead of a join/aggregate? Check with SQL echo/logging on a
  request.
- **Pagination**: do paginated endpoints actually enforce a max page size, or
  can a client request `limit=999999`? Do they return total count / has-more
  info, or just a page of raw rows with no way to know if there's more?
- **Error handling**: what does `/customers/{id}/orders` return for a
  malformed ID vs a well-formed but nonexistent one — same 404, or does a bad
  ID crash with a 500? Try it.
- **Currency/float handling**: is money stored/computed as float anywhere
  (rounding risk) or as integer paise / Decimal? Flag if float.
- **Frontend**: does `npm run build` succeed cleanly? Does the Customer
  Lookup tab handle a nonexistent customer ID without a raw stack trace in
  the UI?
- **Tests**: is there at least one test that would fail if the ₹5,741-style
  bug were reintroduced? If not, add one — a reviewer will notice if your
  test suite couldn't have caught the bug you just found.

## 5. README accuracy pass

Read the README top to bottom as if you've never seen the code. Flag any
claim that isn't backed by something you just verified in steps 1–4
(numbers, idempotency claims, "6 endpoints", test counts, etc.). Fix any
claim that's now wrong given whatever you find above.

## Output format

Give me:
1. A short list of **confirmed bugs/inconsistencies** (with root cause, not
   just symptom) — this is the important part.
2. A short list of things that checked out fine — don't need detail, just
   confirmation.
3. Any README edits needed as a result.
4. If you fixed anything, show the diff and re-run the affected tests to
   prove the fix.

Do not just say "everything looks good" without having actually run the
verification steps above — I want the real numbers you computed, not a
summary judgment.
