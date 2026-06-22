# E06 Mistral all-in-one smoke

Status: opt-in, skipped by default.

## Command

```bash
DAWN_MISTRAL_SMOKE=1 \
DAWN_MISTRAL_ENDPOINT=https://mistral.example.invalid:8989 \
DAWN_MISTRAL_AUTH_VALUE=<test-project-auth-value> \
DAWN_MISTRAL_WORKFLOW_KEY=maintenance-host-precheck \
DAWN_MISTRAL_WORKFLOW_NAME=portal.maintenance_host_precheck.v1 \
DAWN_MISTRAL_TEST_PROJECT_ID=<test-project-id> \
DAWN_MISTRAL_NO_PRODUCTION_ACTION_PROOF=read_only_workflow_lookup \
DAWN_MISTRAL_CACERT=/path/to/test-ca.pem \
make test-integration
```

`DAWN_MISTRAL_CACERT` is optional when the system trust store already contains the test CA.

## Evidence

The smoke test performs only a read-only Mistral workflow definition lookup:

- method: `GET`;
- endpoint source: `DAWN_MISTRAL_ENDPOINT`;
- workflow key: `DAWN_MISTRAL_WORKFLOW_KEY`;
- Mistral workflow name: `DAWN_MISTRAL_WORKFLOW_NAME`;
- correlation ID: generated per test as `e06-mistral-smoke-<uuid>`;
- no production action proof: `read_only_workflow_lookup`.

The test fails if `DAWN_MISTRAL_SMOKE=1` is set without the complete explicit configuration. Without
`DAWN_MISTRAL_SMOKE=1`, it is skipped and does not contact Mistral.

This evidence proves that the configured all-in-one Mistral endpoint can read the allowlisted workflow
definition. It does not prove production workflow execution safety, SIEM delivery, IAM/PAM/SoD
controls, or rollback of mutating OpenStack actions.
