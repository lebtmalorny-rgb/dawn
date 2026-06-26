# E09 Ansible sync bundle

- Stage: E09 Ansible sync bundle
- Scope: local-only export; remote sync remains separately approved
- Live execution status: `pending_external_evidence`
- Source commit: `c227ef6b27ec`
- Bundle schema: `e09-ansible-sync-bundle/v1`
- runtime secret value: absent; DB/MQ URLs remain external runtime secret inputs

## Bundle contents

| Path | Bytes | SHA256 |
|---|---:|---|
| `examples/cloud-ui-vars.yml.example` | 530 | `4d20263a69dd32f996f90f409c8c9eaf725531fdc6c1ccac466a42abdefb69f0` |
| `playbooks/cloud-ui-preflight.yml` | 934 | `92b8e46966a77b1dec9dcd0ecfcf798f8c20eae98290ff5e6997e41dbc4a29ad` |
| `roles/cloud_ui/defaults/main.yml` | 15571 | `401419751cc84c5e2c3df7d6047c240a06f860439448226acd6d1ec049b9ea16` |
| `roles/cloud_ui/handlers/main.yml` | 128 | `62c2c87dd735ccbc1a8a62a808a912cf9b42913c193451c0c62e14379938dfd8` |
| `roles/cloud_ui/tasks/config.yml` | 954 | `2f2a631028d8039261da016bccd8ee09926a9242cc8a0a3f8f09671e534dbe77` |
| `roles/cloud_ui/tasks/containers.yml` | 701 | `e6a8329ff57dfaf64644a75073c225c1ae46dc7943ef1dab0009f7924eb66b6f` |
| `roles/cloud_ui/tasks/lifecycle.yml` | 1346 | `cf0b352e7b059bcb76b42b1785f32ef2d0dcedf25a31860ed10af914671f7ddc` |
| `roles/cloud_ui/tasks/main.yml` | 487 | `71648231c1ad1a0d52beec06da6ca6cb6f4c7a8469fc044b3e9fd315e93748fc` |
| `roles/cloud_ui/tasks/migration.yml` | 375 | `2c8d50320a9584b09509cdbb7981e9fea2c2ef61548e1ee54d3f9e98af35f2fc` |
| `roles/cloud_ui/tasks/validate.yml` | 3539 | `13db400fc8828a49b8b25ac8606a1cfa69512056bc754bc21bb04309f2549614` |
| `roles/cloud_ui/templates/cloud-ui-backend.env.j2` | 293 | `f3edd855122ef628778f3fc703acfcc1be296005e285c1375f19e66ad18b215c` |
| `roles/cloud_ui/templates/cloud-ui-frontend.conf.j2` | 408 | `fe451a53b3f938efe2bd880f89b23988917b57a93e14f46b904315568275756a` |
| `roles/cloud_ui/templates/cloud-ui-haproxy.cfg.j2` | 2629 | `3981096919b464a2857a81c4be6bc3cc0b46292652da05072632fe2aa62a4f50` |

## Operator note

Set ANSIBLE_ROLES_PATH=roles or configure an equivalent Ansible roles path.

This local-only slice does not copy the bundle to a host, run live mutating Kolla
actions, remediate DB/MQ auth, inspect containers, validate HAProxy/TLS or execute
rollback.

## Remaining blockers

- remote sync remains separately approved;
- DB/MQ auth remediation remains `pending_external_evidence`;
- live reconfigure, 12-container inspection, HAProxy/TLS, SELinux and rollback remain pending.
