# E09 Ansible sync bundle

- Stage: E09 Ansible sync bundle
- Scope: local-only export; remote sync remains separately approved
- Live execution status: `pending_external_evidence`
- Source commit: `e09-aio-kolla-cli-path-local`
- Bundle schema: `e09-ansible-sync-bundle/v1`
- runtime secret value: absent; DB/MQ URLs remain external runtime secret inputs

## Bundle contents

| Path | Bytes | SHA256 |
|---|---:|---|
| `examples/cloud-ui-aio-kolla-vars.yml.example` | 600 | `65f9689afbd8bc77471c7d3001f21c1e64d001449eb9dc489d82dd55b9001759` |
| `examples/cloud-ui-vars.yml.example` | 530 | `4d20263a69dd32f996f90f409c8c9eaf725531fdc6c1ccac466a42abdefb69f0` |
| `playbooks/cloud-ui-aio-reconfigure.yml` | 256 | `428d015b15838cfba257a78fc0102bc03abd71ba94c8c32def16663b055cfbfa` |
| `playbooks/cloud-ui-preflight.yml` | 957 | `0cd6efbf124ebb2efbfefd9a0a989edb9f8de29e3172556d78176395da1dccde` |
| `roles/cloud_ui/defaults/main.yml` | 16445 | `d0036afe4ff9fe4dd867b06b188e7bed1d709d1f4979c2d78c2fa05c400eb1ba` |
| `roles/cloud_ui/handlers/main.yml` | 128 | `62c2c87dd735ccbc1a8a62a808a912cf9b42913c193451c0c62e14379938dfd8` |
| `roles/cloud_ui/tasks/config.yml` | 994 | `732d109d520ba585775c6a6232a34d9052d068d4060dbd2afb1456a4cd3f2e83` |
| `roles/cloud_ui/tasks/containers.yml` | 701 | `e6a8329ff57dfaf64644a75073c225c1ae46dc7943ef1dab0009f7924eb66b6f` |
| `roles/cloud_ui/tasks/lifecycle.yml` | 1346 | `cf0b352e7b059bcb76b42b1785f32ef2d0dcedf25a31860ed10af914671f7ddc` |
| `roles/cloud_ui/tasks/live-aio.yml` | 5160 | `c4114cc425c532ff38621f4384945418e03a4cf6dfcd7c8e0eeffcf036a4e8e8` |
| `roles/cloud_ui/tasks/main.yml` | 637 | `bc163e652927b8994d0d0d3d064994d9ca3933d94782f1b24953b9356e6154b3` |
| `roles/cloud_ui/tasks/migration.yml` | 375 | `2c8d50320a9584b09509cdbb7981e9fea2c2ef61548e1ee54d3f9e98af35f2fc` |
| `roles/cloud_ui/tasks/validate.yml` | 3539 | `13db400fc8828a49b8b25ac8606a1cfa69512056bc754bc21bb04309f2549614` |
| `roles/cloud_ui/templates/cloud-ui-backend.env.j2` | 293 | `f3edd855122ef628778f3fc703acfcc1be296005e285c1375f19e66ad18b215c` |
| `roles/cloud_ui/templates/cloud-ui-frontend.conf.j2` | 408 | `fe451a53b3f938efe2bd880f89b23988917b57a93e14f46b904315568275756a` |
| `roles/cloud_ui/templates/cloud-ui-haproxy.cfg.j2` | 2629 | `3981096919b464a2857a81c4be6bc3cc0b46292652da05072632fe2aa62a4f50` |

## Operator note

Set ANSIBLE_ROLES_PATH=roles or configure an equivalent Ansible roles path.

This local-only export does not itself copy the bundle to a host, run live mutating
Kolla actions, remediate DB/MQ auth, inspect containers, validate HAProxy/TLS or
execute rollback. Separate 2026-06-28 AIO role evidence is recorded in
`docs/generated/e09-deployment-smoke-evidence.md`.

## Remaining blockers

- remote sync remains separately approved for each target stand;
- DB/MQ auth remediation remains `pending_external_evidence` for new stands;
- upstream Kolla `site.yml`/tag integration, 12-container inspection, HAProxy/TLS,
  SELinux and failed-update rollback remain pending.
