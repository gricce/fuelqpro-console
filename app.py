from flask import Flask, request, render_template
import os
import datetime
import collections
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

# Setup logging queue
log_messages = collections.deque(maxlen=100)

def log_message(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    logger.info(message)
    log_messages.append(log_entry)

# Import services after logging is configured
from services.whatsapp_service import process_whatsapp_message
from services.openai_service import verify_openai_api
from services.storage_service import verify_gcs
from models.user import user_data_store
import config

# WhatsApp webhook
@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    start_time = time.time()
    log_message(">>> Entered webhook")
    
    try:
        sender = request.form.get('From')
        incoming_msg = request.form.get('Body', '').strip()
        
        log_message(f">>> Received message: '{incoming_msg}' from {sender}")
        
        # Process the message and get response
        response = process_whatsapp_message(sender, incoming_msg, log_message)
        
        log_message(f">>> Total processing time: {time.time() - start_time:.2f}s")
        return response
    
    except Exception as e:
        log_message(f">>> ERROR: {str(e)}")
        from twilio.twiml.messaging_response import MessagingResponse
        resp = MessagingResponse()
        resp.message("Ocorreu um erro ao processar sua solicitação. Por favor, tente novamente.")
        return str(resp)

# Admin dashboard
@app.route("/fuelqpro/console", methods=["GET"])
def dashboard():
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    recent_logs = list(log_messages)
    
    # Get Firebase data for display
    firebase_stats = {}
    try:
        from services.firebase_service import initialize_firebase
        from firebase_admin import firestore
        if initialize_firebase(log_message):
            db = firestore.client()
            users_ref = db.collection('users')
            
            # Count users
            firebase_stats['user_count'] = len(list(users_ref.stream()))
            
            # Count PDF plans
            firebase_stats['pdf_count'] = 0
            for user in users_ref.stream():
                user_data = user.to_dict()
                firebase_stats['pdf_count'] += len(user_data.get('pdf_plans', []))
            
            # Get recent interactions
            interactions = []
            recent_interactions = (
                db.collectionGroup('interactions')
                .order_by('timestamp', direction=firestore.Query.DESCENDING)
                .limit(10)
                .stream()
            )
            
            for interaction in recent_interactions:
                interaction_data = interaction.to_dict()
                interactions.append(interaction_data)
            
            firebase_stats['recent_interactions'] = interactions
            
    except Exception as e:
        firebase_stats['error'] = str(e)
    
    return render_template(
        "dashboard.html", 
        timestamp=timestamp, 
        logs=recent_logs,
        users=user_data_store,
        user_count=len(user_data_store),
        firebase_stats=firebase_stats,
        base_url="/fuelqpro/console"
    )

# Health check endpoint
@app.route("/fuelqpro/console/health", methods=["GET"])
def health_check():
    return "OK", 200

# API verification endpoints  
@app.route("/fuelqpro/console/verify-api-key", methods=["GET"])
def verify_api_key_endpoint():
    return verify_openai_api()

@app.route("/fuelqpro/console/verify-gcs", methods=["GET"])
def verify_gcs_endpoint():
    return verify_gcs()

# File download endpoint
@app.route("/fuelqpro/console/download/<filename>", methods=["GET"])
def download_file(filename):
    """Serve files from Google Cloud Storage"""
    try:
        bucket = config.storage_bucket
        if not bucket:
            return "Storage not configured", 500
            
        blob = bucket.blob(filename)
        if not blob.exists():
            return "File not found", 404
            
        content = blob.download_as_bytes()
        
        return Response(
            content,
            mimetype='application/pdf',
            headers={"Content-Disposition": f"attachment;filename={filename}"}
        )
    except Exception as e:
        log_message(f">>> ERROR downloading file: {str(e)}")
        return "Error downloading file", 500
    
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    log_message(f"Starting application on port {port}")
    app.run(debug=False, host="0.0.0.0", port=port)
