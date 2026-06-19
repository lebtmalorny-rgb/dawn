import pika


def check_rabbitmq(rabbitmq_url: str) -> str:
    parameters = pika.URLParameters(rabbitmq_url)
    parameters.socket_timeout = 3
    parameters.blocked_connection_timeout = 3

    connection: pika.BlockingConnection | None = None
    try:
        connection = pika.BlockingConnection(parameters)
        return "reachable"
    finally:
        if connection is not None and connection.is_open:
            connection.close()
