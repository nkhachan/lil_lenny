import smtplib
import os
import numpy as np
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from agents.voice import OpenAIVoiceModelProvider, VoicePipelineConfig
from audio_player import AudioPlayer


async def send_email(
    subject: str,
    body: str,
    sender_email: str,
    receiver_email: str,
    smtp_server: str = "smtp.gmail.com",
    smtp_port: int = 587,
    password: str = None
) -> None:
    """
    Send an email using SMTP.

    Args:
        subject: Email subject line
        body: Email body text
        sender_email: Email address of the sender
        receiver_email: Email address of the receiver
        smtp_server: SMTP server address (default: "smtp.gmail.com")
        smtp_port: SMTP server port (default: 587)
        password: Email password (if None, uses GMAIL_PASSWORD env var)

    Raises:
        Exception: If email sending fails
    """
    if password is None:
        password = os.environ.get("GMAIL_PASSWORD")
        if not password:
            raise ValueError("Email password must be provided or set in GMAIL_PASSWORD environment variable")

    # Create the email message
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    # Connect to the SMTP server and send email
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Secure the connection
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        print("Email sent successfully!")
    except Exception as e:
        print(f"Error sending email: {e}")
        raise


async def play_text_tts(text: str) -> None:
    """
    Convert text to speech and play it using OpenAI's TTS model.

    Args:
        text: The text to convert to speech and play
    """
    provider = OpenAIVoiceModelProvider()
    tts_model = provider.get_tts_model(model_name="gpt-4o-mini-tts")

    audio_bytes = bytearray()
    async for chunk in tts_model.run(text, VoicePipelineConfig().tts_settings):
        audio_bytes.extend(chunk)

    audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
    audio_array = np.concatenate([audio_array, np.zeros(24000, dtype=audio_array.dtype)])

    with AudioPlayer() as player:
        player.add_audio(audio_array)
