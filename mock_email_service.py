def send_email(to_email: str, subject: str, body: str, attachment_url: str) -> None:
    print(f"\n--- Mock Email Sent ---")
    print(f"To: {to_email}")
    print(f"Subject: {subject}")
    print(f"Body: {body}")
    print(f"Attachment URL: {attachment_url}")
    print("------------------------\n")
