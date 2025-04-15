import hashlib

# Simple user credentials (in production, use a proper database)
USERS = {
    'Daniel': hashlib.sha256('password123'.encode()).hexdigest()
}

def authenticate_user(username, password):
    if username in USERS:
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
        return USERS[username] == hashed_pw
    return False