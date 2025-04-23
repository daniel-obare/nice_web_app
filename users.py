import hashlib
from sqlalchemy import create_engine, text
from datetime import datetime
import re, os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database credentials
DB_CONFIG = {
    'dbname': os.getenv('dbname'),
    'user': os.getenv('user'),
    'password': os.getenv('password'),
    'host': os.getenv('host'),
    'port': os.getenv('port')
}

def get_db_engine():
    db_url = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}"
    return create_engine(db_url)

def to_snake_case(name):
    """Convert a string to lowercase snake_case."""
    name = re.sub(r'[\s-]+', '_', name)  # Replace spaces or hyphens with underscore
    name = re.sub(r'(?<!^)(?=[A-Z])', '_', name)  # Add underscore before capital letters
    return name.lower()  # Convert to lowercase

# Function to fetch users from the database
def fetch_users(engine):
    try:
        with engine.connect() as conn:
            query = text("SELECT username, password FROM raw.users")
            result = conn.execute(query)
            rows = result.fetchall()
            
            # Create a dictionary with usernames and hashed passwords
            users = {}
            for row in rows:
                username, password = row
                # Hash the password since the script expects hashed passwords
                hashed_password = hashlib.sha256(password.encode()).hexdigest()
                users[username] = hashed_password
            
            return users
    
    except Exception as e:
        print(f"Error fetching users: {e}")
        return {}

# Create the database engine
engine = get_db_engine()

# Load users from the database
USERS = fetch_users(engine)

def authenticate_user(username, password):
    if username in USERS:
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
        return USERS[username] == hashed_pw
    return False