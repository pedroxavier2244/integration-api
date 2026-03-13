import aiosmtplib
import structlog
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path

from app.core.config import settings

logger = structlog.get_logger()

_template_env = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "email_templates"),
    autoescape=select_autoescape(["html"]),
)


async def _send(to: str, subject: str, html_body: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = settings.SMTP_FROM
    msg["To"]      = to
    msg.attach(MIMEText(html_body, "html"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            start_tls=settings.SMTP_TLS,
        )
        logger.info("email_sent", to=_mask_email(to), subject=subject)
    except Exception as exc:
        logger.error("email_send_failed", to=_mask_email(to), subject=subject, error=str(exc))
        raise


def _mask_email(email: str) -> str:
    try:
        user, domain = email.split("@")
        return f"{user[:2]}***@{domain}"
    except Exception:
        return "***"


async def send_invite_email(to: str, full_name: str, token: str) -> None:
    link = f"{settings.FRONTEND_URL}/auth/set-password?token={token}"
    html = _render("invite.html", full_name=full_name, link=link, expires_hours=48)
    await _send(to, subject="Bem-vindo — defina sua senha de acesso", html_body=html)


async def send_reset_password_email(to: str, full_name: str, token: str) -> None:
    link = f"{settings.FRONTEND_URL}/auth/reset-password?token={token}"
    html = _render("reset_password.html", full_name=full_name, link=link, expires_hours=1)
    await _send(to, subject="Redefinição de senha", html_body=html)


def _render(template_name: str, **kwargs) -> str:
    return _template_env.get_template(template_name).render(**kwargs)
