from dataclasses import dataclass


@dataclass
class RabbitMQConnectionConfig:
    host: str
    port: int
    user: str
    password: str
    exchange_name: str | None

    @property
    def connection_string(self) -> str:
        return f"amqp://{self.user}:{self.password}@{self.host}:{self.port}"
