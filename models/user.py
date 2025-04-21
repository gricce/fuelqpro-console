from services.firebase_service import get_user_data, save_user_data
from firebase_admin import firestore  # Add this import
import logging 


# In-memory user data store (for backward compatibility)
user_data_store = {}

class UserProfile:
    """User profile and conversation state management"""
    
    def __init__(self, user_id):
        self.user_id = user_id
        self.step = 0
        self.profile = {}
        self.asking_pdf = False
    
    @classmethod
    def get_user(cls, user_id):
        """Get or create a user profile from Firebase"""
        # Try to get from Firebase first
        firebase_data = get_user_data(user_id)
        
        if firebase_data:
            # Use data from Firebase
            if user_id not in user_data_store:
                user_data_store[user_id] = {}
            
            # Update in-memory store
            user_data_store[user_id] = {
                'step': firebase_data.get('step', 0),
                'profile': firebase_data.get('profile', {}),
                'asking_pdf': firebase_data.get('asking_pdf', False)
            }
        elif user_id not in user_data_store:
            # Create new user
            user_data_store[user_id] = {"step": 0, "profile": {}}
            # Save to Firebase
            save_user_data(user_id, {
                'step': 0,
                'profile': {},
                'whatsapp_id': user_id
            })
        
        return user_data_store[user_id]
    
    @classmethod
    def reset_user(cls, user_id):
        """Reset a user's profile data"""
        try:
            # Reset in-memory data
            reset_data = {"step": 0, "profile": {}}
            user_data_store[user_id] = reset_data
            
            # Update in Firebase - with error handling
            try:
                from firebase_admin import firestore
                save_user_data(user_id, {
                    'step': 0,
                    'profile': {},
                    'reset_at': firestore.SERVER_TIMESTAMP
                })
            except Exception as firebase_error:
                logging.error(f"Firebase error during reset: {str(firebase_error)}")
                # Continue even if Firebase fails - don't let Firebase errors break the bot
            
            return reset_data
        except Exception as e:
            logging.error(f"Error in reset_user: {str(e)}")
            # Return a default reset data anyway
            return {"step": 0, "profile": {}}
    
    @classmethod
    def update_profile(cls, user_id, field, value):
        """Update a field in the user's profile"""
        if user_id not in user_data_store:
            cls.get_user(user_id)
        
        if "profile" not in user_data_store[user_id]:
            user_data_store[user_id]["profile"] = {}
            
        user_data_store[user_id]["profile"][field] = value
        
        # Update in Firebase
        firebase_data = {
            'profile': user_data_store[user_id]["profile"]
        }
        save_user_data(user_id, firebase_data)
        
        return user_data_store[user_id]
    
    @classmethod
    def advance_step(cls, user_id):
        """Advance to the next step in the questionnaire"""
        if user_id not in user_data_store:
            cls.get_user(user_id)
            
        user_data_store[user_id]["step"] = user_data_store[user_id].get("step", 0) + 1
        
        # Update in Firebase
        save_user_data(user_id, {
            'step': user_data_store[user_id]["step"]
        })
        
        return user_data_store[user_id]["step"]
    
    @classmethod
    def set_asking_pdf(cls, user_id, asking=True):
        """Set the asking_pdf flag"""
        if user_id not in user_data_store:
            cls.get_user(user_id)
            
        user_data_store[user_id]["asking_pdf"] = asking
        
        # Update in Firebase
        save_user_data(user_id, {
            'asking_pdf': asking
        })
        
        return user_data_store[user_id]