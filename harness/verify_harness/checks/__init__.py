"""The battery's check_* step functions, grouped by the evidence they read
(ADR 2026-07-18 check-sync-decomposition): lint (static tools over the
source), sync (rendered-tree parity and content invariants), suites
(subprocess suite runners). Step order stays the launcher's dispatch list.
Not a manifest: no imports here."""
