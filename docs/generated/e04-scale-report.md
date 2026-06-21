# E04.6 Synthetic scale report

Scope: synthetic/local evidence only; not production MariaDB/HA evidence.

This report is generated from the portal read model populated by synthetic reconciliation in an in-memory SQLite database. It does not contact external OpenStack services, Docker, or live infrastructure.

## Dataset

- instances: 10000
- hypervisors: 1000
- default page size: 50
- max page size: 200
- sample iterations per scenario: 20

## Synchronization

- status: success
- instances seen: 10000
- hypervisors seen: 1000
- generation: 1
- elapsed seconds: 3.218597
- peak Python memory MiB: 3.622

## Read-model scenarios

| Scenario | Resource | Page size | Rows returned | p95 seconds | SQL p95 | SQL max | SQLite EXPLAIN summary |
|---|---|---:|---:|---:|---:|---:|---|
| `instances_default_page` | instances | 50 | 50 | 0.006855 | 5 | 5 | SEARCH instances USING INDEX ix_instances_project_status (cloud_id=? AND region_id=? AND deleted_at=?); USE TEMP B-TREE FOR ORDER BY |
| `instances_filtered_project_status` | instances | 50 | 50 | 0.003270 | 5 | 5 | SEARCH instances USING INDEX ix_instances_project_status (cloud_id=? AND region_id=? AND deleted_at=? AND project_id=? AND status=?) |
| `hypervisors_default_page` | hypervisors | 50 | 50 | 0.004783 | 5 | 5 | SEARCH hypervisors USING INDEX ix_hypervisors_service (cloud_id=? AND region_id=? AND deleted_at=?); USE TEMP B-TREE FOR ORDER BY |
| `hypervisors_filtered_service_status_az` | hypervisors | 50 | 50 | 0.003753 | 5 | 5 | SEARCH hypervisors USING INDEX ix_hypervisors_az (cloud_id=? AND region_id=? AND availability_zone=?) |

## Findings

- No blocking findings for synthetic SQLite read-model list scenarios.

## DKB evidence

- DKB-77/82: records reproducible synthetic evidence for documented list API performance and generated documentation.
- DKB-01/03/12: demonstrates bounded read-model list access without browser-side full inventory loading.
- DKB-46/49: includes sync status and freshness-related read-model evidence.
