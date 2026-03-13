import ssl
import orjson

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

from core.config import env
from core.kafka.kafka_ssl_files_generator import generate_kafka_connection_files
from core.logger import logger

KAFKA_BOOTSTRAP = env.aiven_kafka_bootstrap
TOPIC = env.aiven_kafka_topic


def create_ssl_context() -> ssl.SSLContext:
    ssl_context = ssl.create_default_context(cafile="ca.pem")
    ssl_context.load_cert_chain(certfile="service.cert", keyfile="service.key")
    return ssl_context


def build_producer() -> AIOKafkaProducer:
    return AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=orjson.dumps,
        security_protocol="SSL",
        ssl_context=create_ssl_context(),
        # Reliability
        acks="all",  # wait for all ISR replicas to acknowledge
        enable_idempotence=True,  # exactly-once delivery semantics
        # Throughput / batching
        compression_type="lz4",
        linger_ms=10,  # wait up to 10ms to batch messages
        max_batch_size=16384,
        # Retries
        request_timeout_ms=30_000,
        retry_backoff_ms=300,
    )


class KafkaProducerManager:
    """Manages producer lifecycle. Use as an app-level singleton (e.g. FastAPI lifespan)."""

    def __init__(self):
        self._producer: AIOKafkaProducer | None = None

    async def start(self):
        generate_kafka_connection_files(env)  # side-effect deferred to explicit startup
        self._producer = build_producer()
        await self._producer.start()
        logger.info("Kafka producer started (bootstrap=%s)", KAFKA_BOOTSTRAP)

    async def stop(self):
        if self._producer:
            await self._producer.stop()
            logger.info("Kafka producer stopped")

    async def send(self, topic: str, value: dict, key: bytes | None = None) -> None:
        if not self._producer:
            raise RuntimeError("Producer is not running — call start() first")
        try:
            await self._producer.send_and_wait(topic, value=value, key=key)
        except KafkaError:
            logger.exception("Failed to send message to topic %s", topic)
            raise

    # Convenience shortcut for the default topic
    async def publish(self, value: dict, key: bytes | None = None) -> None:
        await self.send(TOPIC, value, key)


kafka_producer = KafkaProducerManager()
