from PIL import Image
import io
import smtplib
from email.message import EmailMessage
from app.core.config import settings


def process_image_to_aspect(
    image_data: bytes, target_size: tuple[int, int]
) -> io.BytesIO:
    """
    Processes an image to match a specific aspect ratio by cropping it centrally
    and then resizing it to the target dimensions.
    The output image is saved in WebP format.
    """

    img = Image.open(io.BytesIO(image_data))
    src_w, src_h = img.size
    tgt_w, tgt_h = target_size
    src_ratio = src_w / src_h
    tgt_ratio = tgt_w / tgt_h

    if src_ratio > tgt_ratio:
        # Source is wider than target; crop horizontally
        new_w = int(tgt_ratio * src_h)
        left = (src_w - new_w) // 2
        img = img.crop((left, 0, left + new_w, src_h))

    elif src_ratio < tgt_ratio:
        # Source is taller than target; crop vertically
        new_h = int(src_w / tgt_ratio)
        top = (src_h - new_h) // 2
        img = img.crop((0, top, src_w, top + new_h))

    # Convert to RGB and resize to the exact target size
    img = img.convert("RGB").resize((tgt_w, tgt_h))

    # Save the image to ByteIO object as WebP and return it.
    out = io.BytesIO()
    img.save(out, format="WebP")
    out.seek(0)

    return out


def send_otp_email(to_email: str, otp: str):
    msg = EmailMessage()
    msg["Subject"] = "BRIDGE email verification OTP"
    msg["From"] = settings.MAIL
    msg["To"] = to_email

    # Simple email body
    body = f"Your OTP for verification is: {otp}"
    msg.set_content(body)

    # In the future, you can use templates here
    # msg.add_alternative(html_template, subtype='html')

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(settings.MAIL, settings.MAIL_PASSKEY)
        server.send_message(msg)
    print(f"Email sent to {to_email}")
