"""handoff — the public API of the handoff-log runtime.

This package is the composition root's library: the entry point handoff.py and
grading.py compose it, and `import handoff; handoff.<name>` resolves every
public name below (ADR 2026-07-17 runtime-package-layout). The layer map is the
tree — schema is the byte contract (ACL), records the typed model, routing the
deterministic policy, view the human-facing board. The four modules own the
logic; this file re-exports their public names in the explicit `X as X` form
that mypy's no-implicit-reexport requires, so the surface is declared once and
checked.
"""

# The two underscore names are deliberate exports: the schema↔dataclass parity
# suite (tests/handoff/test_records.py) checks the registries through the
# package. Every other underscore name is module-internal — reach it via its
# owning submodule, not here.
from .records import (
    _MAPPERS as _MAPPERS,
    _RECORD_TYPES as _RECORD_TYPES,
    GRADER as GRADER,
    HUMAN as HUMAN,
    PLAN_ENGINE as PLAN_ENGINE,
    RETRY_CAP as RETRY_CAP,
    ROSTER_FLOOR as ROSTER_FLOOR,
    SUBSTANTIVE as SUBSTANTIVE,
    BuildFailure as BuildFailure,
    BuildPass as BuildPass,
    ConsultationRequest as ConsultationRequest,
    ConsultationResponse as ConsultationResponse,
    DesignBlock as DesignBlock,
    DesignDocAutofix as DesignDocAutofix,
    DispatchStart as DispatchStart,
    Facet as Facet,
    Facets as Facets,
    Features as Features,
    Finding as Finding,
    GraderFeatures as GraderFeatures,
    GraderVerdict as GraderVerdict,
    HandoffRecord as HandoffRecord,
    MemoryUpdate as MemoryUpdate,
    Pattern as Pattern,
    PlanBasis as PlanBasis,
    PrdAutofix as PrdAutofix,
    PrdEntry as PrdEntry,
    ReviewFeedback as ReviewFeedback,
    ReviewPlan as ReviewPlan,
    Risk as Risk,
    ScopeOverride as ScopeOverride,
    SourceFinding as SourceFinding,
    UnknownRecord as UnknownRecord,
    parse_record as parse_record,
)
from .routing import (
    Decision as Decision,
)
from .schema import (
    LogEntry as LogEntry,
    SchemaError as SchemaError,
    canonicalize as canonicalize,
    dumps_canonical as dumps_canonical,
    load_schema as load_schema,
    loads_strict as loads_strict,
    parse_log as parse_log,
    read_layout as read_layout,
    resolve_ref as resolve_ref,
    ts_now as ts_now,
    unsupported_keywords as unsupported_keywords,
    validate_record as validate_record,
)
from .view import (
    DIM as DIM,
    GREEN as GREEN,
    accounting as accounting,
    render_view as render_view,
    render_view_md as render_view_md,
)
