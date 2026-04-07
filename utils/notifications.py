"""
utils/notifications.py — Optional email notifications for task assignments.

Set MAIL_USERNAME and MAIL_PASSWORD in your .env to enable.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os


def send_task_notification(
    recipient_email: str,
    task: dict,
    meeting_title: str = 'Meeting'
) -> bool:
    """
    Send an email notification for a task.

    Args:
        recipient_email: Target email address
        task:            { person, task, deadline, priority }
        meeting_title:   Human-readable meeting name

    Returns:
        True on success, False on failure
    """
    mail_user = os.getenv('MAIL_USERNAME', '')
    mail_pass = os.getenv('MAIL_PASSWORD', '')

    if not mail_user or not mail_pass:
        print("⚠️  Email not configured — skipping notification")
        return False

    subject = f"[Action Required] Task from {meeting_title}"
    body = f"""
Hello {task.get('person', 'Team Member')},

A task has been assigned to you from the recent meeting: {meeting_title}

📋 Task:    {task.get('task', 'N/A')}
📅 Deadline: {task.get('deadline', 'Not specified')}
🔥 Priority: {task.get('priority', 'Medium')}

Please ensure this is completed on time.

—
Meeting Analyzer Bot
    """.strip()

    msg = MIMEMultipart()
    msg['From']    = mail_user
    msg['To']      = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(mail_user, mail_pass)
        server.send_message(msg)
        server.quit()
        print(f"📧  Notification sent to {recipient_email}")
        return True
    except Exception as e:
        print(f"❌  Email failed: {e}")
        return False
