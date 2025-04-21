import os
import time
import uuid
import datetime
import firebase_admin
from firebase_admin import credentials, firestore, storage
from firebase_admin.exceptions import FirebaseError

# Firebase credentials path
firebase_credentials_path = os.getenv("FIREBASE_CREDENTIALS", "firebase-credentials.json")

# Firebase clients
db = None
firebase_bucket = None

def initialize_firebase(log_message=print):
    """Initialize Firebase if not already initialized"""
    global db, firebase_bucket

    try:
        log_message(f"Initializing Firebase with project ID: {os.getenv('FIREBASE_PROJECT_ID')}")
        
        if not firebase_admin._apps:
            if os.getenv("K_SERVICE"):
                log_message("Initializing in Cloud environment...")
                firebase_admin.initialize_app(options={
                    'projectId': os.getenv("FIREBASE_PROJECT_ID"),
                    'storageBucket': os.getenv("FIREBASE_STORAGE_BUCKET")
                })
            else:
                log_message("Initializing in local environment...")
                # For local development, try to use application default credentials
                firebase_admin.initialize_app()
                
            log_message("Firebase initialized successfully")
        else:
            log_message("Firebase already initialized")

        db = firestore.client()
        firebase_bucket = storage.bucket()
        
        # Test Firestore connection
        test_ref = db.collection('test').document('test')
        test_ref.set({'test': 'test'})
        test_ref.delete()
        
        log_message("Firestore connection test successful")
        return True

    except Exception as e:
        log_message(f"ERROR initializing Firebase: {str(e)}")
        return False

def get_user_data(user_id, log_message=print):
    if not initialize_firebase(log_message):
        return None

    try:
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()
        if user_doc.exists:
            log_message(f">>> Retrieved user data for {user_id}")
            return user_doc.to_dict()
        log_message(f">>> No data found for user {user_id}")
        return None
    except Exception as e:
        log_message(f">>> ERROR retrieving user data: {str(e)}")
        return None

def save_user_data(user_id, user_data, log_message=print):
    if not initialize_firebase(log_message):
        return False

    try:
        user_data['last_updated'] = firestore.SERVER_TIMESTAMP
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()

        if not user_doc.exists:
            user_data['created_at'] = firestore.SERVER_TIMESTAMP

        user_ref.set(user_data, merge=True)
        log_message(f">>> Saved user data for {user_id}")
        return True

    except Exception as e:
        log_message(f">>> ERROR saving user data: {str(e)}")
        return False

def upload_pdf_to_firebase(pdf_bytes, user_profile, log_message=print):
    if not initialize_firebase(log_message):
        return None

    try:
        filename = f"plans/plan_{user_profile.get('name', 'user')}_{int(time.time())}_{str(uuid.uuid4())[:8]}.pdf"
        filename = filename.replace(' ', '_').lower()

        blob = firebase_bucket.blob(filename)
        blob.upload_from_string(pdf_bytes, content_type='application/pdf')

        url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(days=7),
            method="GET"
        )

        user_id = user_profile.get('whatsapp_id', '')
        if user_id:
            user_ref = db.collection('users').document(user_id)
            user_doc = user_ref.get()
            user_data = user_doc.to_dict() if user_doc.exists else {}

            pdf_list = user_data.get('pdf_plans', [])
            pdf_list.append({
                'filename': filename,
                'created_at': firestore.SERVER_TIMESTAMP,
                'url': url
            })

            user_ref.update({ 'pdf_plans': pdf_list })

        log_message(f">>> PDF uploaded to Firebase: {url}")
        return url

    except Exception as e:
        log_message(f">>> ERROR uploading PDF to Firebase: {str(e)}")
        return None

def log_interaction(user_id, message_type, message_content, response, log_message=print):
    if not initialize_firebase(log_message):
        return False

    try:
        interaction_ref = db.collection('users').document(user_id).collection('interactions').document()
        interaction_data = {
            'timestamp': firestore.SERVER_TIMESTAMP,
            'message_type': message_type,
            'message': message_content,
            'response': response
        }
        interaction_ref.set(interaction_data)
        log_message(f">>> Logged interaction for {user_id}")
        return True

    except Exception as e:
        log_message(f">>> ERROR logging interaction: {str(e)}")
        return False
