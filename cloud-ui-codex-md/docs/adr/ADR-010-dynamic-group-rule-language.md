# ADR-010: Dynamic group rule language

- Status: proposed-default
- Stage: E00
- Owner required: product/security owner

## Context

Dynamic resource groups must allow safe filtering without arbitrary SQL, Python, Jinja, regex or expensive queries.

## Decision

Use a JSON AST DSL compiled to allowlisted backend filters. Default `additionalProperties=false`. Only explicitly allowed resource fields and operators are supported. Complexity, depth, page size and preview limits are enforced server-side.

## Initial allowed shape

```json
{
  "all": [
    {"field": "project_id", "op": "eq", "value": "project-ref"},
    {"field": "status", "op": "in", "value": ["ACTIVE", "SHUTOFF"]}
  ]
}
```

Allowed combinators:

- `all`
- `any`
- `not`

Initial operators:

- `eq`
- `in`
- `prefix`
- `exists`

Initial fields:

- `project_id`
- `status`
- `host_name`
- `availability_zone`
- `flavor_id`
- normalized tag keys/values after E04 schema exists

## Consequences

- Preview and evaluation use the same compiler.
- No raw SQL or user-provided expressions.
- Cross-scope rules are rejected.
- Imported membership retains provenance and does not mutate OpenStack placement.

## Verification

- Invalid operator/field rejected.
- Complexity/depth limit tested.
- Cursor/page limit tested.
- IDOR/cross-scope negative tests.
