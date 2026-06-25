import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ROLE_ROOT = ROOT / "deploy/kolla/ansible/roles/cloud_ui"

HAPROXY_TEMPLATE = (
    "deploy/kolla/ansible/roles/cloud_ui/templates/cloud-ui-haproxy.cfg.j2"
)
EVIDENCE_DOC = "docs/generated/e09-haproxy-tls-network.md"


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def load_yaml(relative_path: str) -> dict:
    return yaml.safe_load(read_text(relative_path))


def load_yaml_list(relative_path: str) -> list[dict]:
    loaded = yaml.safe_load(read_text(relative_path))
    if not isinstance(loaded, list):
        return []
    return loaded


def test_defaults_declare_same_origin_haproxy_route_contract() -> None:
    defaults = load_yaml("deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml")

    assert defaults["cloud_ui_config_version"].startswith("e09.")
    assert defaults["cloud_ui_haproxy_enabled"] is False
    assert defaults["cloud_ui_external_scheme"] == "https"
    assert defaults["cloud_ui_external_fqdn"] == "cloud-ui.example.invalid"
    assert (
        defaults["cloud_ui_public_base_url"]
        == "{{ cloud_ui_external_scheme }}://{{ cloud_ui_external_fqdn }}/"
    )
    assert defaults["cloud_ui_api_public_path"] == "/api/v1/"

    routes = defaults["cloud_ui_haproxy_routes"]
    assert [route["name"] for route in routes] == [
        "cloud_ui_api",
        "cloud_ui_frontend",
    ]
    assert routes[0] == {
        "name": "cloud_ui_api",
        "path_prefix": "{{ cloud_ui_api_public_path }}",
        "service": "cloud_ui_api",
        "backend": "cloud_ui_api",
        "health_check_path": "/api/v1/health/ready",
        "upstream_scheme": "{{ cloud_ui_haproxy_backend_scheme }}",
        "upstream_port": "{{ cloud_ui_backend_listen_port }}",
    }
    assert routes[1] == {
        "name": "cloud_ui_frontend",
        "path_prefix": "/",
        "service": "cloud_ui_frontend",
        "backend": "cloud_ui_frontend",
        "health_check_path": "/",
        "upstream_scheme": "{{ cloud_ui_haproxy_frontend_scheme }}",
        "upstream_port": "{{ cloud_ui_frontend_listen_port }}",
    }


def test_defaults_declare_tls_timeout_header_and_network_policy() -> None:
    defaults = load_yaml("deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml")

    assert defaults["cloud_ui_haproxy_bind_address"] == "{{ kolla_external_vip_address }}"
    assert defaults["cloud_ui_haproxy_external_port"] == 443
    assert defaults["cloud_ui_haproxy_tls_min_version"] == "TLSv1.2"
    assert defaults["cloud_ui_haproxy_backend_tls_mode"] == "internal_http"
    assert defaults["cloud_ui_haproxy_backend_tls_mode_allowed"] == [
        "internal_http",
        "backend_tls",
        "backend_mtls",
    ]
    assert defaults["cloud_ui_haproxy_backend_scheme"] == "http"
    assert defaults["cloud_ui_haproxy_frontend_scheme"] == "http"

    assert defaults["cloud_ui_haproxy_timeouts"] == {
        "connect": "5s",
        "client": "60s",
        "server": "60s",
        "http_request": "10s",
    }
    assert defaults["cloud_ui_haproxy_max_body_bytes"] == 16 * 1024 * 1024
    assert defaults["cloud_ui_haproxy_trusted_proxy_headers"] == [
        "X-Forwarded-For",
        "X-Forwarded-Proto",
        "X-Forwarded-Host",
        "X-Request-ID",
    ]
    assert defaults["cloud_ui_haproxy_security_headers"] == {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer",
    }
    assert defaults["cloud_ui_management_network_acl_required"] is True
    assert defaults["cloud_ui_management_network_acl_status"] == "pending_external_evidence"
    assert defaults["cloud_ui_forbidden_network_flows"] == [
        "browser_to_openstack_api",
        "browser_to_database",
        "browser_to_rabbitmq",
        "browser_to_vault",
        "frontend_to_openstack_service_database",
        "portal_consumer_to_openstack_rpc_wildcard",
    ]


def test_haproxy_template_declares_same_origin_routes_and_safe_headers() -> None:
    template = read_text(HAPROXY_TEMPLATE)

    for expected in [
        "frontend cloud_ui_external",
        "bind {{ cloud_ui_haproxy_bind_address }}:{{ cloud_ui_haproxy_external_port }} ssl crt {{ cloud_ui_haproxy_tls_cert_bundle_path }} ssl-min-ver {{ cloud_ui_haproxy_tls_min_version }}",
        "acl cloud_ui_api_path path_beg {{ cloud_ui_api_public_path }}",
        "use_backend cloud_ui_api if cloud_ui_api_path",
        "default_backend cloud_ui_frontend",
        "backend cloud_ui_api",
        "option httpchk GET /api/v1/health/ready",
        "{% for host in groups[cloud_ui_api_group] | default([]) %}",
        "server cloud_ui_api_{{ loop.index }} {{ hostvars[host].ansible_host | default(host) }}:{{ cloud_ui_backend_listen_port }} check",
        "backend cloud_ui_frontend",
        "option httpchk GET /",
        "{% for host in groups[cloud_ui_frontend_group] | default([]) %}",
        "server cloud_ui_frontend_{{ loop.index }} {{ hostvars[host].ansible_host | default(host) }}:{{ cloud_ui_frontend_listen_port }} check",
        "http-request set-header X-Forwarded-Proto https if { ssl_fc }",
        "http-request set-header X-Forwarded-Host %[req.hdr(Host)]",
        "http-request set-header X-Request-ID %[unique-id] unless { req.hdr(X-Request-ID) -m found }",
        "http-response set-header X-Content-Type-Options nosniff",
        "http-response set-header X-Frame-Options DENY",
        "http-response set-header Referrer-Policy no-referrer",
        "http-request deny deny_status 413 if { req.hdr(content-length),int gt {{ cloud_ui_haproxy_max_body_bytes }} }",
    ]:
        assert expected in template

    lower_template = template.lower()
    for forbidden in [
        "begin private key",
        "private_key",
        "password",
        "token",
        "application_credential",
        "clouds.yaml",
        "admin" + "123",
    ]:
        assert forbidden not in lower_template


def test_config_task_renders_haproxy_contract_without_live_reload() -> None:
    config_tasks = load_yaml_list("deploy/kolla/ansible/roles/cloud_ui/tasks/config.yml")
    config_text = read_text("deploy/kolla/ansible/roles/cloud_ui/tasks/config.yml")

    assert "cloud-ui-haproxy" in config_text
    assert "cloud-ui-haproxy.cfg.j2" in config_text
    assert "{{ cloud_ui_config_root }}/cloud-ui-haproxy/cloud-ui-haproxy.cfg" in config_text
    assert "kolla-ansible reconfigure" not in config_text
    assert "service:" not in config_text
    assert "haproxy reload" not in config_text.lower()

    rendered_templates = [
        task.get("ansible.builtin.template") or task.get("template")
        for task in config_tasks
        if isinstance(task, dict)
    ]
    rendered_templates = [
        template for template in rendered_templates if isinstance(template, dict)
    ]
    assert any(
        template.get("src") == "cloud-ui-haproxy.cfg.j2"
        and template.get("dest")
        == "{{ cloud_ui_config_root }}/cloud-ui-haproxy/cloud-ui-haproxy.cfg"
        for template in rendered_templates
    )


def test_validate_task_checks_haproxy_route_policy_bounds() -> None:
    validate_text = read_text("deploy/kolla/ansible/roles/cloud_ui/tasks/validate.yml")

    for expected in [
        "cloud_ui_external_scheme == 'https'",
        "cloud_ui_external_fqdn != 'cloud-ui.example.invalid' or not cloud_ui_haproxy_enabled",
        "cloud_ui_api_public_path == '/api/v1/'",
        "cloud_ui_haproxy_routes | length == 2",
        "cloud_ui_haproxy_routes[0].name == 'cloud_ui_api'",
        "cloud_ui_haproxy_routes[1].name == 'cloud_ui_frontend'",
        "cloud_ui_haproxy_tls_min_version in ['TLSv1.2', 'TLSv1.3']",
        "cloud_ui_haproxy_backend_tls_mode in cloud_ui_haproxy_backend_tls_mode_allowed",
        "cloud_ui_haproxy_max_body_bytes > 0",
        "cloud_ui_management_network_acl_required | bool",
    ]:
        assert expected in validate_text


def test_e09_role_scope_recognizes_haproxy_as_current_slice() -> None:
    role_test = read_text("tests/test_e09_kolla_ansible_role.py")

    assert "test_role_scope_excludes_later_e09_work" in role_test
    forbidden_block = re.search(
        r"for forbidden in \[(?P<body>.*?)\]:",
        role_test,
        flags=re.DOTALL,
    )
    assert forbidden_block is not None
    assert '"haproxy"' not in forbidden_block.group("body")
    assert HAPROXY_TEMPLATE in role_test


def test_e09_haproxy_tls_network_evidence_and_matrices_are_updated() -> None:
    evidence = read_text(EVIDENCE_DOC)
    tls_matrix = read_text("docs/generated/tls-matrix.md")
    network_matrix = read_text("docs/generated/network-flow-matrix.md")
    risk_register = read_text("docs/generated/risk-register.md")
    dkb_traceability = read_text("docs/11_DKB_TRACEABILITY.md")

    for expected in [
        "Stage: E09.6 HAProxy/TLS/network",
        "same-origin route",
        "`/api/v1/` -> `cloud_ui_api`",
        "`/` -> `cloud_ui_frontend`",
        "`/api/v1/health/ready`",
        "trusted proxy headers",
        "pending_external_evidence",
        "ДКБ-22.02/23.02/24",
        "ДКБ-65/66",
        "not a live HAProxy deployment",
    ]:
        assert expected in evidence

    for expected in [
        "E09.6 repository route contract",
        "cloud-ui.example.invalid",
        "backend TLS mode: `internal_http` by default",
    ]:
        assert expected in tls_matrix

    for expected in [
        "Cloud UI same-origin route contract",
        "HAProxy -> Cloud UI frontend containers",
        "HAProxy -> Cloud UI API containers",
        "management ACL proof pending",
    ]:
        assert expected in network_matrix

    assert "R-066" in risk_register
    assert "E09.6 HAProxy/TLS/network" in dkb_traceability
    assert "production approved" not in evidence.lower()
