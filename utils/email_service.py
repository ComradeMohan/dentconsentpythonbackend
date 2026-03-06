import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configure these or load from environment
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "sandeepdental175@gmail.com"
SMTP_PASS = "dcqa pvwg oexd anvw"

def send_email(to_email: str, subject: str, body: str):
    """Sends an email using SMTP."""
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'html'))
        
        # Connect to server
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
        server.quit()
        
        print(f"Email sent successfully to {to_email}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def send_welcome_email(to_email: str, full_name: str, role: str):
    subject = "Welcome to DentConsent!"
    body = f"<h2>Welcome to DentConsent, {full_name}!</h2><p>You have successfully registered as a {role}.</p>"
    return send_email(to_email, subject, body)

def send_otp_email(to_email: str, otp: str, action: str):
    subject = f"Your OTP for {action} - DentConsent"
    body = f"<h2>Your OTP is: <b>{otp}</b></h2><p>Use this code for {action}. It expires in 10 minutes.</p>"
    return send_email(to_email, subject, body)
