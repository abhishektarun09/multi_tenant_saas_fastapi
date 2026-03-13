import base64
from pathlib import Path


def generate_kafka_connection_files(settings, output_dir: str = "."):

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    file_map = {
        "ca.pem": settings.AIVEN_KAFKA_CA_PEM_B64,
        "service.cert": settings.AIVEN_KAFKA_SERVICE_CERT_B64,
        "service.key": settings.AIVEN_KAFKA_SERVICE_KEY_B64,
    }

    for filename, b64_value in file_map.items():
        decoded = base64.b64decode(b64_value)

        file_path = output_path / filename
        with open(file_path, "wb") as f:
            f.write(decoded)
