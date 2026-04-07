import secrets

def generate_token(length=20):
    return secrets.token_urlsafe(length)[:length]