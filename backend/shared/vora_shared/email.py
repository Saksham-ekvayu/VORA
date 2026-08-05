"""Email sending + HTML template rendering.

Mirrors Node's `email.service.js` (nodemailer + Gmail SMTP + `{{var}}`
template placeholders), but using aiosmtplib so services stay fully async.
"""

import logging
import random
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

import aiosmtplib

from vora_shared.config import Settings, get_settings

logger = logging.getLogger(__name__)

_template_cache: dict[str, str] = {}


def generate_otp() -> str:
    """6-digit numeric OTP — matches Node's `Math.floor(100000 + Math.random() * 900000)`."""
    return str(random.randint(100000, 999999))


def load_template(templates_dir: str | Path, name: str, variables: dict | None = None) -> str:
    """Load an HTML template from `templates_dir/{name}.html` and replace
    `{{key}}` placeholders, matching Node's `loadTemplate` helper."""
    cache_key = f"{Path(templates_dir).resolve()}::{name}"
    template = _template_cache.get(cache_key)
    if template is None:
        path = Path(templates_dir) / f"{name}.html"
        template = path.read_text(encoding="utf-8")
        _template_cache[cache_key] = template

    all_vars: dict = {"currentYear": datetime.now().year, "userName": "User"}
    all_vars.update(variables or {})

    rendered = template
    for key, value in all_vars.items():
        rendered = rendered.replace("{{" + key + "}}", "" if value is None else str(value))
    return rendered


async def send_email(
    to: str,
    subject: str,
    html: str,
    settings: Settings | None = None,
) -> bool:
    """Send an HTML email via Gmail SMTP (587/STARTTLS), matching Node's
    nodemailer transporter config. Returns False (never raises) on failure,
    same contract as Node's `sendEmail` returning a boolean."""
    settings = settings or get_settings()
    if not settings.email_user or not settings.email_pass:
        logger.error("Email not sent — EMAIL_USER/EMAIL_PASS not configured")
        return False

    message = EmailMessage()
    message["From"] = settings.email_from or settings.email_user
    message["To"] = to
    message["Subject"] = subject
    message.add_alternative(html, subtype="html")

    try:
        await aiosmtplib.send(
            message,
            hostname="smtp.gmail.com",
            port=587,
            start_tls=True,
            username=settings.email_user,
            password=settings.email_pass,
            validate_certs=False,
        )
        return True
    except Exception:
        logger.exception("Error sending email")
        return False
