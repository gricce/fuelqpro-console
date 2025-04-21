from services.firebase_service import initialize_firebase, firestore
import bcrypt
import logging

def init_default_admin():
    try:
        initialize_firebase()
        db = firestore.client()
        
        # Check if admin user exists
        admin_ref = db.collection('admin_users').where('username', '==', 'admin').limit(1)
        existing_admin = admin_ref.get()
        
        if len(existing_admin) > 0:
            print("Default admin user already exists")
            return
        
        # Create default admin user
        password = 'admin'
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        db.collection('admin_users').add({
            'username': 'admin',
            'password': hashed.decode('utf-8'),
            'name': 'Administrator',
            'email': 'admin@example.com',
            'created_at': firestore.SERVER_TIMESTAMP,
            'last_login': None
        })
        
        print("Default admin user created successfully")
        print("Username: admin")
        print("Password: admin")
        print("Please change these credentials after first login!")
        
    except Exception as e:
        print(f"Error creating default admin: {str(e)}")

if __name__ == "__main__":
    init_default_admin()