# Scale profile

- Stage: E00
- Status: provisional
- Rule: every production number must be replaced by measured or owner-provided evidence before P3.

## Provisional test profile

The following values come from `docs/01_SCOPE_AND_REQUIREMENTS.md` and are used only until real values are approved.

| Dimension | Provisional value | Source | Status |
|---|---:|---|---|
| Instances | 10,000 | NFR-03 | provisional |
| Hypervisors | 1,000 | NFR-03 | provisional |
| Concurrent UI users | 50 | NFR-03 | provisional |
| Portal audit test rows | 1,000,000 | NFR-03 | provisional |
| Large table UX model | 100,000+ rows synthetic where module requires it | FR-16 | provisional |
| Default page size | 50 | NFR-03 | provisional |
| Max page size | 200 | NFR-03/API rules | provisional |
| p95 list API from read model | <= 2 seconds | NFR-03 | provisional |
| Mutating API acknowledgement | <= 1 second to `operation_id` | NFR-03 | provisional |

## Production values to collect

| Dimension | Current value | Owner/method |
|---|---|---|
| Clouds/regions | 1 observed region: `RegionOne` | service catalog via `/etc/kolla/admin-openrc.sh` |
| Projects | 2 observed | Keystone read-only inventory |
| Instances | 0 observed | Nova inventory |
| Hypervisors | 1 observed | Nova inventory |
| Networks/subnets/ports | unknown | Neutron inventory if in scope |
| Volumes/images | unknown | Cinder/Glance inventory if in scope |
| Compute services / Neutron agents / Cinder services | unknown | OpenStack service health inventory |
| Watcher audits/action plans/recommendations | unknown | Watcher inventory and test fixtures |
| Masakari segments/hosts/notifications | unknown | Masakari inventory and monitor coverage |
| Telemetry metric cardinality | unknown | Ceilometer/Gnocchi/Prometheus/Aetos owner |
| Topology graph nodes/edges | unknown | synthetic graph generator and read model measurement |
| Live event subscribers | unknown | product/SRE estimate |
| Live event burst rate | unknown | OpenStack notifications/operation telemetry sample |
| Resource groups | unknown | product owner estimate |
| Workflow definitions | unknown | workflow owner |
| Change rate | unknown | OpenStack notifications/telemetry sample |
| Audit event rate | unknown | SIEM/OpenStack audit sample |
| Concurrent users | unknown | product/SRE estimate |
| API request rate | unknown | Horizon/API logs if available |
| Acceptable stale age | unknown | product/SRE decision |
| RPO/RTO | unknown | platform/SRE decision |
| DB connection limit | unknown | MariaDB owner |
| RabbitMQ rate/queue limits | unknown | messaging owner |
| OpenStack API rate limits | unknown | OpenStack owner |

## Current test cloud counts

Read-only CLI inventory on 2026-06-19:

| Resource | Count |
|---|---:|
| projects | 2 |
| users | 8 |
| hypervisors | 1 |
| servers all projects | 0 |
| images | 0 |
| networks | 2 |
| volumes all projects | 0 |

Current test cloud is too small for E04/E10 scale evidence. Synthetic datasets remain required for provisional performance tests.

## Initial performance budgets

| Path | Budget | Evidence required |
|---|---:|---|
| `GET /api/v1/instances` p95 | <= 2 s for 10k synthetic rows | E04 synthetic scale report |
| `GET /api/v1/hypervisors` p95 | <= 2 s for 1k synthetic rows | E04 synthetic scale report |
| Group preview p95 | <= 2 s for constrained rule | E05 scale report |
| Operation submit p95 | <= 1 s to durable `operation_id` | E06 integration report |
| Operation event stream latency p95 | unknown | E06/E10 SSE/polling report |
| Topology expansion p95 | <= 2 s for bounded synthetic graph page until replaced | E04/E10 graph report |
| Capacity dashboard p95 | <= 2 s for pre-aggregated synthetic metrics until replaced | E10 dashboard report |
| Watcher recommendation list p95 | <= 2 s for bounded page until replaced | E06/E10 report |
| Masakari recovery timeline p95 | <= 2 s for bounded page until replaced | E06/E10 report |
| Audit search p95 | <= 3 s for constrained query | E07/E10 report |
| Reconciliation full sync | unknown | E04/E10 measurement |
| Event freshness lag | unknown | E04/E10 measurement |

## Test data rules

- deterministic synthetic seed;
- no personal, business or production payload;
- UUIDs scoped by `cloud_id` and `region_id`;
- canary secret strings used only for leakage tests;
- enough cardinality for filters, indexes and group rules;
- sanitized reports committed only as summaries.
