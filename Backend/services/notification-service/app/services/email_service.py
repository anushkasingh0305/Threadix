from app.utils.logger import setup_logger

logger = setup_logger(__name__)


async def send_notification_email(
    recipient_email: str,
    actor_username: str,
    notif_type: str,
    thread_id: int,
):
    """
    Email delivery is not implemented.
    Planned improvement: integrate an email provider (SendGrid, Resend, SES).
    """
    logger.debug(
        f'Email delivery skipped (not implemented) → {recipient_email} [{notif_type}]'
    )
