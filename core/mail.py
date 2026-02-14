from fastapi_mail import FastMail, ConnectionConfig, MessageSchema, MessageType
from pathlib import Path
from core.config import env

BASE_DIR = Path(__file__).resolve().parent

mail_config = ConnectionConfig(
    MAIL_USERNAME=env.mail_username,
    MAIL_PASSWORD=env.mail_password,
    MAIL_FROM=env.mail_from,
    MAIL_PORT=env.mail_port,
    MAIL_SERVER=env.mail_server,
    MAIL_FROM_NAME=env.mail_from_name,
    MAIL_STARTTLS=env.mail_starttls,
    MAIL_SSL_TLS=env.mail_ssl_tls,
    USE_CREDENTIALS=env.use_credentials,
    VALIDATE_CERTS=env.validate_certs,
    TEMPLATE_FOLDER=Path(BASE_DIR, "templates"),
)

mail = FastMail(config=mail_config)


def create_message(
    recipients: list[str],
    subject: str,
    template_body: dict,
):
    message = MessageSchema(
        recipients=recipients,
        subject=subject,
        subtype=MessageType.html,
        template_body=template_body,
    )

    return message
