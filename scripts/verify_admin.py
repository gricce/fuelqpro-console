import firebase_admin
from firebase_admin import credentials, firestore
import os

def verify_admin():
    try:
        firebase_admin.initialize_app(options={
            'projectId': os.getenv("FIREBASE_PROJECT_ID")
        })
        
        db = firestore.client()
        admin_users = db.collection('admin_users').stream()
        
        print("Existing admin users:")
        for admin in admin_users:
            admin_data = admin.to_dict()
            print(f"ID: {admin.id}")
            print(f"Username: {admin_data.get('username')}")
            print(f"Name: {admin_data.get('name')}")
            print("---")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    verify_admin()