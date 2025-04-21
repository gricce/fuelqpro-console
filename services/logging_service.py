import os
import datetime
import traceback
import json
try:
    from flask import request
except ImportError:
    request = None

# Create a logs directory if it doesn't exist
def ensure_logs_directory():
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    return logs_dir

# Log categories
LOG_WHATSAPP = 'whatsapp'
LOG_OPENAI = 'openai'
LOG_STORAGE = 'storage'
LOG_SYSTEM = 'system'
LOG_ERROR = 'error'

def log_event(category, message, data=None, user_id=None):
    """
    Log an event to the appropriate log file
    
    Args:
        category (str): Category of the log (whatsapp, openai, storage, system, error)
        message (str): Log message
        data (dict, optional): Additional data to log
        user_id (str, optional): User ID associated with the log
    """
    try:
        logs_dir = ensure_logs_directory()
        
        # Create a timestamp
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        # Format the log entry
        log_entry = {
            'timestamp': timestamp,
            'category': category,
            'message': message,
            'user_id': user_id,
        }
        
        if data:
            # Convert any non-serializable objects to strings
            serializable_data = {}
            for key, value in data.items():
                if isinstance(value, (str, int, float, bool, list, dict, type(None))):
                    serializable_data[key] = value
                else:
                    try:
                        serializable_data[key] = str(value)
                    except:
                        serializable_data[key] = f"<Unserializable type: {type(value).__name__}>"
            
            log_entry['data'] = serializable_data
        
        # Get request info if available
        try:
            if request:
                log_entry['request'] = {
                    'ip': request.remote_addr,
                    'user_agent': request.user_agent.string,
                    'path': request.path,
                    'method': request.method,
                }
        except:
            # Not in a request context
            pass
        
        # Format the log string
        log_parts = [
            f"[{timestamp}]",
            f"[{category.upper()}]",
        ]
        
        if user_id:
            log_parts.append(f"[User: {user_id}]")
            
        log_parts.append(message)
        
        if data:
            try:
                log_parts.append(json.dumps(serializable_data, indent=2))
            except:
                log_parts.append(str(serializable_data))
        
        log_text = " ".join(log_parts)
        
        # Write to category-specific log file
        category_log_file = os.path.join(logs_dir, f"{category}.log")
        with open(category_log_file, 'a', encoding='utf-8') as f:
            f.write(log_text + "\n")
        
        # Also write to all.log
        all_log_file = os.path.join(logs_dir, "all.log")
        with open(all_log_file, 'a', encoding='utf-8') as f:
            f.write(log_text + "\n")
            
        # For errors, also include the traceback
        if category == LOG_ERROR:
            error_details = traceback.format_exc()
            with open(category_log_file, 'a', encoding='utf-8') as f:
                f.write(error_details + "\n")
            with open(all_log_file, 'a', encoding='utf-8') as f:
                f.write(error_details + "\n")
        
        return True
        
    except Exception as e:
        print(f"Error logging event: {str(e)}")
        print(traceback.format_exc())
        return False

def log_whatsapp(message, data=None, user_id=None):
    """Log a WhatsApp bot interaction"""
    return log_event(LOG_WHATSAPP, message, data, user_id)

def log_openai(message, data=None, user_id=None):
    """Log an OpenAI API request"""
    return log_event(LOG_OPENAI, message, data, user_id)

def log_storage(message, data=None, user_id=None):
    """Log a storage operation (PDF, etc.)"""
    return log_event(LOG_STORAGE, message, data, user_id)

def log_system(message, data=None):
    """Log a system event"""
    return log_event(LOG_SYSTEM, message, data)

def log_error(message, error=None, user_id=None):
    """Log an error event"""
    data = None
    if error:
        data = {'error': str(error)}
    return log_event(LOG_ERROR, message, data, user_id)