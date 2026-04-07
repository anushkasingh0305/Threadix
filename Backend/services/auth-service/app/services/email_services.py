from app.utils.logger import logger


def send_reset_email(email: str, token: str):
    """
    Email delivery is not implemented.
    Planned improvement: integrate an email provider (SendGrid, Resend, SES).
    Token is logged to console for development use only.
    """
    logger.warning(
        f'Email delivery not implemented — reset token for {email}: {token}'
    )