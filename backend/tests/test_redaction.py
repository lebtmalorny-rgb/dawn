from cloud_ui.logging import redact_mapping


def test_redact_mapping_hides_secret_like_values() -> None:
    data = {
        "database_url": "mysql+pymysql://user:password@db:3306/cloud_ui",
        "rabbitmq_url": "amqp://user:password@rabbitmq:5672/%2Fcloud-ui",
        "normal": "visible",
        "token": "abc",
    }

    redacted = redact_mapping(data)

    assert redacted["database_url"] == "***"
    assert redacted["rabbitmq_url"] == "***"
    assert redacted["token"] == "***"
    assert redacted["normal"] == "visible"
