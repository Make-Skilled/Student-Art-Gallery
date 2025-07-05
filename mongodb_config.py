import os
from dotenv import load_dotenv
from pymongo import MongoClient
from gridfs import GridFS
import jwt
import bcrypt
from datetime import datetime, timedelta

load_dotenv()

# MongoDB Atlas connection
MONGODB_URI = os.getenv("MONGODB_URI")
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-this")

# Initialize MongoDB client
client = MongoClient(MONGODB_URI)
db = client.student_art_gallery
fs = GridFS(db)

# Collections
users_collection = db.users
artworks_collection = db.artworks
likes_collection = db.likes
comments_collection = db.comments

# Authentication helpers
def hash_password(password):
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def verify_password(password, hashed):
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

def generate_token(user_id):
    """Generate JWT token for user"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def verify_token(token):
    """Verify JWT token and return user_id"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

# Database helpers
def get_user_by_id(user_id):
    """Get user by ID"""
    try:
        from bson import ObjectId
        # Convert string user_id to ObjectId if needed
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)
        return users_collection.find_one({'_id': user_id})
    except Exception as e:
        print(f"Error getting user by ID: {e}")
        return None

def get_user_by_email(email):
    """Get user by email"""
    return users_collection.find_one({'email': email})

def create_user(user_data):
    """Create a new user"""
    user_data['created_at'] = datetime.utcnow()
    user_data['password'] = hash_password(user_data['password'])
    result = users_collection.insert_one(user_data)
    return str(result.inserted_id)

def save_file_to_db(file_data, filename, content_type):
    """Save file to MongoDB using GridFS"""
    file_id = fs.put(file_data, filename=filename, content_type=content_type)
    return str(file_id)

def get_file_from_db(file_id):
    """Get file from MongoDB using GridFS"""
    try:
        from bson import ObjectId
        # Convert string file_id to ObjectId
        if isinstance(file_id, str):
            file_id = ObjectId(file_id)
        file_obj = fs.get(file_id)
        return file_obj
    except Exception as e:
        print(f"Error getting file from DB: {e}")
        return None

def delete_file_from_db(file_id):
    """Delete file from MongoDB using GridFS"""
    try:
        fs.delete(file_id)
        return True
    except:
        return False 