import time
import uuid
import datetime
import config

# In storage_service.py
def upload_pdf_to_storage(pdf_bytes, user_profile, log_message=print):
    """Upload a PDF to Google Cloud Storage and return a URL"""
    bucket = config.storage_bucket
    
    if not bucket:
        log_message(">>> ERROR: Google Cloud Storage bucket not available")
        return None
    
    try:
        # Generate a unique filename
        filename = f"plan_{user_profile.get('name', 'user')}_{int(time.time())}_{str(uuid.uuid4())[:8]}.pdf"
        filename = filename.replace(' ', '_').lower()
        
        # Create a new blob and upload the PDF
        blob = bucket.blob(filename)
        blob.upload_from_string(pdf_bytes, content_type='application/pdf')
        
        # Create a download URL through our own application
        # This assumes our app is deployed at a URL like https://fuelqpro-xxxx-xx.a.run.app
        app_url = os.getenv("APP_URL", "https://fuelqpro-xxxx-xx.a.run.app")
        url = f"{app_url}/download/{filename}"
        
        log_message(f">>> PDF uploaded to {url}")
        
        return url
    
    except Exception as e:
        log_message(f">>> ERROR uploading PDF to storage: {str(e)}")
        return None
    
def verify_gcs():
    """Verify that Google Cloud Storage is properly configured"""
    bucket = config.storage_bucket
    
    if not bucket:
        return "Google Cloud Storage bucket not configured or not accessible", 400
    
    try:
        # Try to upload a test file
        test_blob = bucket.blob("test_file.txt")
        test_blob.upload_from_string("This is a test file to verify GCS access.", content_type="text/plain")
        
        # Generate a signed URL for testing
        expiration_time = datetime.timedelta(minutes=5)
        url = test_blob.generate_signed_url(
            version="v4",
            expiration=expiration_time,
            method="GET"
        )
        
        # Delete the test file
        test_blob.delete()
        
        return f"Google Cloud Storage is working correctly. Test URL was: {url}", 200
    except Exception as e:
        return f"Google Cloud Storage verification failed: {str(e)}", 400