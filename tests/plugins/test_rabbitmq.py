from logging import Logger

from spakky.application.application_context import ApplicationContext
from spakky.application.interfaces.pluggable import IPluggable
from spakky_rabbitmq.plugins.rabbitmq import RabbitMQPlugin
from spakky_rabbitmq.post_processor import RabbitMQPostProcessor


def test_rabbitmq_plugin_register(logger: Logger) -> None:
    context: ApplicationContext = ApplicationContext()
    plugin: IPluggable = RabbitMQPlugin(logger)
    plugin.register(context)

    assert context.post_processors == {RabbitMQPostProcessor}
