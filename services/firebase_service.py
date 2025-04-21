import os
import time
import uuid
import datetime
import firebase_admin
from firebase_admin import credentials, firestore, storage
from firebase_admin.exceptions import FirebaseError

def initialize_firebase(log_message=print):
    """Initialize Firebase if not already initialized"""
    global db, firebase_bucket

    try:
        project_id = os.getenv("FIREBASE_PROJECT_ID")
        storage_bucket = os.getenv("FIREBASE_STORAGE_BUCKET")
        
        if not project_id or not storage_bucket:
            log_message(f"Missing required environment variables. Project ID: {project_id}, Storage Bucket: {storage_bucket}")
            return False

        log_message(f"Initializing Firebase with project ID: {project_id} and bucket: {storage_bucket}")
        
        # If Firebase is already initialized, delete the default app and reinitialize
        if firebase_admin._apps:
            log_message("Cleaning up existing Firebase app")
            # Fix: Create a list of apps to avoid modifying dict during iteration
            app_list = list(firebase_admin._apps.values())
            for app in app_list:
                firebase_admin.delete_app(app)

        # Initialize Firebase with both project ID and storage bucket
        firebase_admin.initialize_app(options={
            'projectId': project_id,
            'storageBucket': storage_bucket
        })
        log_message("Firebase initialized successfully with application default credentials")

        # Initialize Firestore
        db = firestore.client()
        log_message("Firestore client initialized")

        # Initialize Storage bucket
        firebase_bucket = storage.bucket()
        log_message("Storage bucket initialized")
        
        # Test Firestore connection
        test_ref = db.collection('test').document('test')
        test_ref.set({'test': 'test'})
        test_ref.delete()
        log_message("Firestore connection test successful")

        # Test Storage bucket connection
        test_blob = firebase_bucket.blob('test.txt')
        test_blob.upload_from_string('test')
        test_blob.delete()
        log_message("Storage bucket connection test successful")
        
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

def simple_initialize_firebase():
    """
    A simplified version of the Firebase initialization function
    that avoids common pitfalls and focuses on reliable initialization.
    """
    global db, firebase_bucket
    
    # Force set environment variables if not present
    if not os.getenv("FIREBASE_PROJECT_ID"):
        os.environ["FIREBASE_PROJECT_ID"] = "fuelqpro"
    
    if not os.getenv("FIREBASE_STORAGE_BUCKET"):
        os.environ["FIREBASE_STORAGE_BUCKET"] = "fuelqpro.firebasestorage.app"
    
    try:
        print("Starting Firebase initialization...")
        
        # Check for existing Firebase apps and clean up safely
        if firebase_admin._apps:
            print("Found existing Firebase apps, cleaning up...")
            try:
                # Convert keys to a list first to avoid the dictionary changed size error
                app_names = list(firebase_admin._apps.keys())
                for app_name in app_names:
                    if app_name in firebase_admin._apps:  # Check again in case it was deleted
                        print(f"Deleting app: {app_name}")
                        firebase_admin.delete_app(firebase_admin._apps[app_name])
            except Exception as e:
                print(f"Error cleaning up Firebase apps: {str(e)}")
                print("Continuing with initialization anyway...")
        
        # Initialize Firebase with only the project ID first
        print(f"Initializing Firebase with project ID: {os.environ.get('FIREBASE_PROJECT_ID')}")
        app = firebase_admin.initialize_app(options={
            'projectId': os.environ.get("FIREBASE_PROJECT_ID")
        })
        print(f"Firebase app initialized with name: {app.name}")
        
        # Initialize Firestore
        print("Initializing Firestore client...")
        db = firestore.client()
        print("Firestore client initialized.")
        
        # Test Firestore with a simple operation
        print("Testing Firestore connection...")
        test_doc = db.collection('test').document('test_doc')
        test_doc.set({'test': 'test_value'})
        test_result = test_doc.get()
        if test_result.exists and test_result.to_dict().get('test') == 'test_value':
            print("Firestore connection test successful!")
            test_doc.delete()  # Clean up
        else:
            print("Firestore connection test failed!")
        
        # Try initializing storage separately
        try:
            print(f"Initializing Storage with bucket: {os.environ.get('FIREBASE_STORAGE_BUCKET')}")
            firebase_bucket = storage.bucket(os.environ.get("FIREBASE_STORAGE_BUCKET"))
            print("Storage bucket initialized.")
        except Exception as storage_error:
            print(f"Error initializing Storage (this is not critical for authentication): {str(storage_error)}")
        
        print("Firebase initialization completed successfully!")
        return True
    
    except Exception as e:
        log_message(f">>> ERROR logging interaction: {str(e)}")
        return False