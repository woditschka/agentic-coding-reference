"""The battery's domain package (ADR 2026-07-18 check-sync-decomposition).

The launcher harness/verify-harness.py keeps the authoritative step-list header
and the ordered dispatch; this package holds the parts: text (pure helpers,
the leaf), battery (the aggregator and run harness), and checks/ (the step
functions, grouped by the evidence they read). The internal import graph is
one-directional — launcher → checks → battery → text — and checker-enforced
by battery step 1g. Not a manifest: no imports here."""
