How this project implements the catalog in Java and Spring Boot.

### Building Blocks

| Pattern | Implementation |
|---------|----------------|
| Value object, aggregate | Immutable Java `record`; collections via `List.copyOf()` / `Map.copyOf()` |
| Repository | Spring `@Repository`, one per aggregate root; it stores and loads that aggregate and nothing else |
| Application service | Spring `@Service`; it sequences one use case across collaborators |
| Adapter | Spring `@Component`; it adapts one external system or one kind of I/O |
| Domain service | Plain class of static pure methods; no state, no injected dependency, no stereotype annotation |
| Anti-corruption mapper | Static pure method, `from{Source}()` / `to{Target}()`; a complex mapping delegates to a plain stateless class; no instance state, no injected dependency, no stereotype annotation |
| Configuration | `@ConfigurationProperties` record, validated at startup, in the owning module's `config/` |

A Spring stereotype annotation is the one marker of a bean: `@Repository`, `@Service`, `@Component`, or `@Configuration`. Neither state nor injected dependencies decide bean-ness. The stereotype names the bean's role, so a use case that drifted into an adapter is visible at its declaration. A `@ConfigurationProperties` record binds settings and sits outside this mapping. A stateless helper over a type the project does not own may be a static utility instead of a bean (§ Naming).

### Logic Placement

A bean orchestrates; domain objects, domain services, and mappers decide. A bean holds four things: the sequence of steps, the I/O and external-service calls, the error and logging policy, and configuration reads. Three things leave it.

| What leaves a bean | Where it goes |
|--------------------|---------------|
| A decision about domain state: a merge rule, how an action applies, a predicate over candidates | A method on the value object when the decision concerns one object; a domain service when it spans several |
| A change of representation: a view model, a prompt input, a filename composition | An anti-corruption mapper |
| Parsing and validation of an external format | An anti-corruption mapper or a domain service |

A behavior method on a domain record takes no dependency. A bean's length tracks the number of steps it sequences; growth signals a missing use case, never room for logic. Placement is checked at code review; no build gate marks it.

### Module Layout

The module's base package is its public API. Internals live in role-named sub-packages: `domain/` for domain services, `mapper/` for mappers, `repository/` for repositories, `config/` for configuration. A further role gets a further role name. Technical-layer packages at application level (`model/`, `service/`, `controller/`) are forbidden.

A sub-package type is public so the whole module can use it; the modularity test's `ApplicationModules.verify()` enforces the boundary, not package-private visibility. A sub-package crosses to another module only through `@NamedInterface("name")` on its `package-info.java`, which the consumer narrows with `allowedDependencies = "module :: name"`. A type moves to the base package only when a cross-module caller needs it, and then in the narrowest form that satisfies the caller. A module still crowded after sub-packaging promotes a sub-package to a nested module; a second top-level module for the same concern is forbidden.

### Java Idioms

| Principle | Rule | Rationale |
|-----------|------|-----------|
| **Map domain types directly when the project owns both ends** | Value objects stay immutable `record`s (or `@Embeddable`); an aggregate may be Hibernate-mapped via field access and a reconstitution constructor — a `protected` no-arg the mapper uses, while the business constructors still enforce invariants. Reserve a DTO/mapper layer for external API or schema contracts. | No boilerplate mapping for owned types; the domain keeps its invariants and stays free of the ORM lifecycle. |
| **Prefer specification annotations over vendor annotations** | Use Jakarta Persistence and Jakarta Validation (`jakarta.persistence.*`, `jakarta.validation.*`); reach for vendor-specific annotations (`org.hibernate.*`, Hibernate Validator extras) only where the specification cannot express the requirement. For serialization, rely on native `record` support and add `@Json*` only when the wire contract requires it. | Standard annotations keep the domain portable across implementations; vendor lock-in is a deliberate exception, not the default. |
| **Modern Java idioms** | Use current Java features: `record` for value objects, `var` for local type inference, `Stream` pipelines over `for`-loops, `Optional` over null checks, pattern matching over type casting, text blocks for multi-line strings. | Modern idioms reduce boilerplate and make intent explicit. |
| **Fluent method chaining** | Prefer chained fluent calls over imperative step-by-step mutation: Stream pipelines, `Optional` chains, AssertJ chains. | Fluent chains read as a single declarative expression with fewer intermediate variables. |

These principles apply equally to production code and test code. Tests are first-class code: they use the same immutable records, streams, fluent chains, and modern Java idioms.
