
import firebase_admin
from firebase_admin import credentials, firestore
import bcrypt
import os

def init_default_admin():
    try:
        print("Initializing Firebase...")
        firebase_admin.initialize_app(options={
            'projectId': os.getenv("FIREBASE_PROJECT_ID")
        })
        
        print("Getting Firestore client...")
        db = firestore.client()
        
        # Check if admin user exists
        print("Checking for existing admin user...")
        admin_ref = db.collection('admin_users').where('username', '==', 'admin').limit(1)
        existing_admin = admin_ref.get()
        
        if len(list(existing_admin)) > 0:
            print("Default admin user already exists")
            return
        
        # Create default admin user
        print("Creating new admin user...")
        password = 'admin'
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        new_admin = db.collection('admin_users').add({
            'username': 'admin',
            'password': hashed.decode('utf-8'),
            'name': 'Administrator',
            'email': 'admin@example.com',
            'created_at': firestore.SERVER_TIMESTAMP,
            'last_login': None
        })
        
        print(f"Default admin user created successfully with ID: {new_admin[1].id}")
        print("Username: admin")
        print("Password: admin")
        print("Please change these credentials after first login!")
        
    except Exception as e:
        print(f"Error creating default admin: {str(e)}")
        raise e

if __name__ == "__main__":
    init_default_admin()

