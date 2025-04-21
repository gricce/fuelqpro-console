from flask import Flask, request, render_template, redirect, url_for, flash, session, jsonify
import os
import datetime
import collections
import time
import logging
import traceback
from functools import wraps
import bcrypt
import firebase_admin
from firebase_admin import credentials, firestore

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'Bv5hqlS2CsklVLlN5A1bgnTIa6l3tY84zZsQQCdo7Zo')

# Initialize Firebase at app startup
try:
    if not firebase_admin._apps:
        firebase_admin.initialize_app(options={
            'projectId': os.getenv("FIREBASE_PROJECT_ID")
        })
    logger.info("Firebase initialized successfully at startup")
except Exception as e:
    logger.error(f"Failed to initialize Firebase at startup: {str(e)}")

# Admin authentication
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# Admin login
@app.route("/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')
        
        logger.info(f"Login attempt for username: {username}")
        
        try:
            # Use the simple_initialize_firebase function from the updated service
            from services.firebase_service import simple_initialize_firebase, db, firestore
            
            logger.info("Attempting to initialize Firebase...")
            init_result = simple_initialize_firebase()
            if not init_result:
                logger.error("Failed to initialize Firebase")
                flash('Authentication error: Firebase initialization failed')
                return render_template("admin/login.html")

            logger.info("Firebase initialized successfully, proceeding with login...")
            
            # Try to find the admin user - first check if we created it with a known ID
            admin_user = None
            
            # First try to get the user with the known document ID
            try:
                admin_user_doc = db.collection('admin_users').document('admin_user').get()
                if admin_user_doc.exists and admin_user_doc.to_dict().get('username') == username:
                    admin_user = admin_user_doc
                    logger.info("Found admin user with direct ID lookup")
            except Exception as e:
                logger.warning(f"Error looking up admin by ID: {str(e)}")
            
            # If not found with direct ID, try query
            if not admin_user:
                try:
                    logger.info(f"Querying admin user with username: {username}...")
                    admin_ref = db.collection('admin_users').where('username', '==', username).limit(1)
                    admin_docs = admin_ref.get()
                    admin_user = next(admin_docs, None)
                    if admin_user:
                        logger.info("Found admin user with query")
                except Exception as e:
                    logger.error(f"Error retrieving admin user by query: {str(e)}")
                    flash('Error retrieving user data')
                    return render_template("admin/login.html")
            
            if admin_user:
                try:
                    admin_data = admin_user.to_dict()
                    
                    # Ensure password is properly encoded for bcrypt
                    stored_password = admin_data.get('password', '')
                    if not stored_password:
                        logger.error("Admin user has no password set")
                        flash('Authentication error: Invalid user data')
                        return render_template("admin/login.html")
                    
                    logger.info("Retrieved admin user data, checking password...")
                    
                    # Get encoded passwords for comparison
                    input_pw = password.encode('utf-8')
                    stored_pw = stored_password.encode('utf-8')
                    
                    logger.info("Comparing password hashes...")
                    
                    # For debugging - check password formats
                    logger.info(f"Input password length: {len(input_pw)}")
                    logger.info(f"Stored password length: {len(stored_pw)}")
                    
                    # Print first few chars of hashed stored password for debugging
                    logger.info(f"Stored password prefix: {stored_pw[:10]}...")
                    
                    if bcrypt.checkpw(input_pw, stored_pw):
                        logger.info("Password correct, logging in...")
                        session['admin_logged_in'] = True
                        session['admin_id'] = admin_user.id
                        session['admin_name'] = admin_data.get('name', username)
                        
                        # Update last login
                        logger.info("Updating last login timestamp...")
                        admin_user.reference.update({
                            'last_login': firestore.SERVER_TIMESTAMP
                        })
                        
                        logger.info("Login successful, redirecting to dashboard...")
                        return redirect(url_for('admin_dashboard'))
                    else:
                        logger.warning("Invalid password")
                        flash('Invalid credentials: Password incorrect')
                except Exception as e:
                    logger.error(f"Password verification error: {str(e)}")
                    flash(f'Authentication error: {str(e)}')
            else:
                logger.warning(f"Admin user not found with username: {username}")
                flash('Invalid credentials: User not found')
            
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            logger.error(traceback.format_exc())
            flash(f'Authentication error: {str(e)}')
            
    return render_template("admin/login.html")

# Admin dashboard
@app.route("/", methods=["GET"])
@admin_required
def admin_dashboard():
    try:
        # Use simple_initialize_firebase instead of initialize_firebase
        from services.firebase_service import simple_initialize_firebase, db, firestore
        
        if not simple_initialize_firebase():
            flash('Error connecting to Firebase')
            return render_template("admin/dashboard.html", error="Firebase connection failed")
        
        # Fetch statistics
        stats = {
            'total_users': 0,
            'total_plans': 0,
            'active_today': 0,
            'plans_today': 0
        }
        
        # Get current date for today's stats
        today = datetime.datetime.now().date()
        
        users_ref = db.collection('users')
        users = users_ref.stream()
        
        for user in users:
            user_data = user.to_dict()
            stats['total_users'] += 1
            stats['total_plans'] += len(user_data.get('pdf_plans', []))
            
            # Check today's activity
            last_activity = user_data.get('last_updated')
            if last_activity and last_activity.date() == today:
                stats['active_today'] += 1
            
            # Count today's plans
            for plan in user_data.get('pdf_plans', []):
                if plan.get('created_at') and plan.get('created_at').date() == today:
                    stats['plans_today'] += 1
        
        # Get recent activities
        activities = []
        try:
            recent_interactions = (
                db.collectionGroup('interactions')
                .order_by('timestamp', direction=firestore.Query.DESCENDING)
                .limit(20)
                .stream()
            )
            
            for interaction in recent_interactions:
                interaction_data = interaction.to_dict()
                activities.append(interaction_data)
        except Exception as e:
            logger.warning(f"Error fetching recent activities: {str(e)}")
        
        return render_template(
            "admin/dashboard.html",
            stats=stats,
            activities=activities,
            timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        logger.error(traceback.format_exc())
        return render_template("admin/dashboard.html", error=str(e))

# User management
@app.route("/users", methods=["GET"])
@admin_required
def admin_users():
    debug_info = []
    try:
        debug_info.append("Starting admin_users route")
        
        # Use simple_initialize_firebase instead of initialize_firebase
        from services.firebase_service import simple_initialize_firebase, db
        
        debug_info.append("Imported Firebase services")
        
        if not simple_initialize_firebase():
            debug_info.append("Firebase initialization failed")
            flash('Error connecting to Firebase')
            return render_template("admin/users.html", error="Firebase connection failed", debug_info=debug_info)

        debug_info.append("Firebase initialized successfully")
        users_ref = db.collection('users')
        
        debug_info.append("Getting users stream")
        users_stream = users_ref.stream()
        
        debug_info.append("Processing users")
        users = []
        
        for user in users_stream:
            try:
                user_data = user.to_dict()
                
                # Handle potential missing or malformed data
                if not user_data:
                    debug_info.append(f"User {user.id} has no data, skipping")
                    continue
                    
                user_data['id'] = user.id
                
                # Sanitize user data to prevent template rendering errors
                if 'profile' in user_data and not isinstance(user_data['profile'], dict):
                    user_data['profile'] = {}
                    
                if 'pdf_plans' in user_data and not isinstance(user_data['pdf_plans'], list):
                    user_data['pdf_plans'] = []
                
                users.append(user_data)
                debug_info.append(f"Added user {user.id} to list")
            except Exception as e:
                debug_info.append(f"Error processing user {user.id}: {str(e)}")
                # Continue with next user
                continue
            
        debug_info.append(f"Processed {len(users)} users total")
        return render_template("admin/users.html", users=users, debug_info=debug_info)
        
    except Exception as e:
        logger.error(f"Users page error: {str(e)}")
        logger.error(traceback.format_exc())
        return render_template("admin/users.html", error=str(e), debug_info=debug_info)
    

# Plans management
@app.route("/plans", methods=["GET"])
@admin_required
def admin_plans():
    debug_info = []
    try:
        debug_info.append("Starting admin_plans route")
        
        # Use simple_initialize_firebase instead of initialize_firebase
        from services.firebase_service import simple_initialize_firebase, db
        
        debug_info.append("Imported Firebase services")
        
        if not simple_initialize_firebase():
            debug_info.append("Firebase initialization failed")
            flash('Error connecting to Firebase')
            return render_template("admin/plans.html", error="Firebase connection failed", debug_info=debug_info)

        debug_info.append("Firebase initialized successfully")
        users_ref = db.collection('users')
        
        debug_info.append("Getting users stream")
        users_stream = users_ref.stream()
        
        debug_info.append("Processing users and plans")
        plans = []
        user_count = 0
        plan_count = 0
        error_count = 0
        
        for user in users_stream:
            try:
                user_count += 1
                user_data = user.to_dict()
                
                # Handle potential missing or malformed data
                if not user_data:
                    debug_info.append(f"User {user.id} has no data, skipping")
                    continue
                
                # Handle missing or malformed pdf_plans
                if 'pdf_plans' not in user_data or not isinstance(user_data['pdf_plans'], list):
                    debug_info.append(f"User {user.id} has no valid pdf_plans, skipping")
                    continue
                
                # Handle missing or malformed profile
                if 'profile' not in user_data or not isinstance(user_data['profile'], dict):
                    user_data['profile'] = {'name': 'Unknown User'}
                
                for plan in user_data.get('pdf_plans', []):
                    try:
                        # Ensure plan is a dictionary
                        if not isinstance(plan, dict):
                            debug_info.append(f"Invalid plan type for user {user.id}, skipping")
                            continue
                            
                        plan_count += 1
                        plan['user_id'] = user.id
                        plan['user_name'] = user_data.get('profile', {}).get('name', 'Unknown')
                        
                        # Handle potential missing created_at
                        if 'created_at' not in plan:
                            plan['created_at'] = datetime.datetime.min
                            
                        plans.append(plan)
                    except Exception as plan_error:
                        error_count += 1
                        debug_info.append(f"Error processing plan for user {user.id}: {str(plan_error)}")
                        continue
                        
            except Exception as user_error:
                error_count += 1
                debug_info.append(f"Error processing user {user.id}: {str(user_error)}")
                continue
        
        debug_info.append(f"Processed {user_count} users, {plan_count} plans, encountered {error_count} errors")
        
        # Sort plans by created_at date, handling potential missing or invalid dates
        try:
            plans.sort(key=lambda x: x.get('created_at', datetime.datetime.min), reverse=True)
            debug_info.append("Plans sorted successfully")
        except Exception as sort_error:
            debug_info.append(f"Error sorting plans: {str(sort_error)}")
            # Fallback: try to sort without using created_at if that's causing issues
            try:
                plans.sort(key=lambda x: x.get('user_name', ''), reverse=False)
                debug_info.append("Plans sorted by username instead")
            except:
                debug_info.append("Unable to sort plans, displaying in original order")
        
        return render_template("admin/plans.html", plans=plans, debug_info=debug_info)
        
    except Exception as e:
        logger.error(f"Plans page error: {str(e)}")
        logger.error(traceback.format_exc())
        return render_template("admin/plans.html", error=str(e), debug_info=debug_info)

# Admin users management
@app.route("/admin-users", methods=["GET"])
@admin_required
def manage_admin_users():
    try:
        # Use simple_initialize_firebase instead of initialize_firebase
        from services.firebase_service import simple_initialize_firebase, db
        
        if not simple_initialize_firebase():
            flash('Error connecting to Firebase')
            return render_template("admin/admin_users.html", error="Firebase connection failed")

        admin_users = []
        
        for admin in db.collection('admin_users').stream():
            admin_data = admin.to_dict()
            admin_data['id'] = admin.id
            admin_data.pop('password', None)
            admin_users.append(admin_data)
            
        return render_template("admin/admin_users.html", admin_users=admin_users)
        
    except Exception as e:
        logger.error(f"Admin users page error: {str(e)}")
        return render_template("admin/admin_users.html", error=str(e))

@app.route("/admin-users", methods=["POST"])
@admin_required
def add_admin_user():
    try:
        # Import the simple_initialize_firebase function
        from services.firebase_service import simple_initialize_firebase, db, firestore
        
        if not simple_initialize_firebase():
            flash('Error connecting to Firebase')
            return redirect(url_for('manage_admin_users'))
            
        username = request.form.get('username')
        password = request.form.get('password')
        name = request.form.get('name')
        email = request.form.get('email')
        
        # Check if username exists
        existing = db.collection('admin_users').where('username', '==', username).limit(1).get()
        if len(list(existing)) > 0:
            flash('Username already exists')
            return redirect(url_for('manage_admin_users'))

        # Hash password
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        db.collection('admin_users').add({
            'username': username,
            'password': hashed.decode('utf-8'),
            'name': name,
            'email': email,
            'created_at': firestore.SERVER_TIMESTAMP,
            'last_login': None
        })
        
        flash('User added successfully')
        return redirect(url_for('manage_admin_users'))
    
    except Exception as e:
        logger.error(f"Error adding user: {str(e)}")
        flash('Error adding user')
        return redirect(url_for('manage_admin_users'))

@app.route("/admin-users/<user_id>", methods=["GET"])
@admin_required
def get_admin_user(user_id):
    try:
        # Import the simple_initialize_firebase function
        from services.firebase_service import simple_initialize_firebase, db
        
        if not simple_initialize_firebase():
            return jsonify({'error': 'Error connecting to Firebase'}), 500
            
        user_doc = db.collection('admin_users').document(user_id).get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            return jsonify({
                'name': user_data.get('name'),
                'email': user_data.get('email')
            })
        return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        logger.error(f"Error getting admin user: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route("/admin-users/<user_id>", methods=["DELETE"])
@admin_required
def delete_admin_user(user_id):
    try:
        # Import the simple_initialize_firebase function
        from services.firebase_service import simple_initialize_firebase, db
        
        if not simple_initialize_firebase():
            return jsonify({'success': False, 'error': 'Error connecting to Firebase'})
            
        user_doc = db.collection('admin_users').document(user_id).get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            if user_data.get('username') == 'admin':
                return jsonify({'success': False, 'error': 'Cannot delete default admin user'})
            
            db.collection('admin_users').document(user_id).delete()
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'User not found'})
    except Exception as e:
        logger.error(f"Error deleting admin user: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route("/admin-users/edit", methods=["POST"])
@admin_required
def edit_admin_user():
    try:
        # Import the simple_initialize_firebase function
        from services.firebase_service import simple_initialize_firebase, db, firestore
        
        if not simple_initialize_firebase():
            flash('Error connecting to Firebase')
            return redirect(url_for('manage_admin_users'))
            
        user_id = request.form.get('user_id')
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        user_ref = db.collection('admin_users').document(user_id)
        
        update_data = {
            'name': name,
            'email': email,
            'updated_at': firestore.SERVER_TIMESTAMP
        }
        
        if password:
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            update_data['password'] = hashed.decode('utf-8')
        
        user_ref.update(update_data)
        
        flash('User updated successfully')
        return redirect(url_for('manage_admin_users'))
    
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        flash('Error updating user')
        return redirect(url_for('manage_admin_users'))

@app.route("/backend-data")
@admin_required
def backend_data():
    """
    Display raw backend data from Firestore for debugging purposes.
    This helps diagnose issues with the bot conversation and data structure.
    """
    debug_info = []
    collections_data = {}
    
    try:
        debug_info.append("Starting backend data route")
        
        # Use simple_initialize_firebase
        from services.firebase_service import simple_initialize_firebase, db
        
        debug_info.append("Imported Firebase services")
        
        if not simple_initialize_firebase():
            debug_info.append("Firebase initialization failed")
            flash('Error connecting to Firebase')
            return render_template("admin/backend_data.html", 
                                   error="Firebase connection failed", 
                                   debug_info=debug_info)

        debug_info.append("Firebase initialized successfully")
        
        # Get a list of all collections
        collections = db.collections()
        collection_names = [collection.id for collection in collections]
        debug_info.append(f"Found collections: {', '.join(collection_names)}")
        
        # Process each collection
        for collection_name in collection_names:
            debug_info.append(f"Processing collection: {collection_name}")
            collection_ref = db.collection(collection_name)
            documents = collection_ref.stream()
            
            collection_docs = []
            for doc in documents:
                try:
                    doc_data = doc.to_dict()
                    
                    # Process timestamps for display
                    processed_data = {}
                    for key, value in doc_data.items():
                        if hasattr(value, 'seconds'):  # It's a timestamp
                            try:
                                processed_data[key] = datetime.datetime.fromtimestamp(value.seconds)
                            except:
                                processed_data[key] = f"Timestamp({value.seconds})"
                        elif isinstance(value, list):
                            # For lists (like pdf_plans), count them and show sample
                            processed_data[key] = f"List with {len(value)} items"
                            if value and len(value) > 0:
                                if isinstance(value[0], dict):
                                    # Show keys of the first item
                                    processed_data[f"{key}_sample"] = f"Keys: {', '.join(value[0].keys())}"
                        else:
                            processed_data[key] = value
                    
                    collection_docs.append({
                        'id': doc.id,
                        'data': processed_data
                    })
                except Exception as e:
                    debug_info.append(f"Error processing document {doc.id}: {str(e)}")
            
            collections_data[collection_name] = collection_docs
        
        # Special handling for users collection - check subcollections
        if 'users' in collection_names:
            debug_info.append("Checking user subcollections")
            users_ref = db.collection('users')
            users = users_ref.stream()
            
            user_subcollections = {}
            for user in users:
                try:
                    # Get user subcollections (like interactions)
                    user_subs = user.reference.collections()
                    sub_names = [sub.id for sub in user_subs]
                    
                    if sub_names:
                        user_subcollections[user.id] = sub_names
                        debug_info.append(f"User {user.id} has subcollections: {', '.join(sub_names)}")
                        
                        # For each subcollection, get a sample document
                        for sub_name in sub_names:
                            sub_ref = user.reference.collection(sub_name)
                            sub_docs = sub_ref.limit(5).stream()
                            
                            sample_docs = []
                            for sub_doc in sub_docs:
                                try:
                                    sub_data = sub_doc.to_dict()
                                    sample_docs.append({
                                        'id': sub_doc.id,
                                        'data': sub_data
                                    })
                                except Exception as e:
                                    debug_info.append(f"Error processing subdocument {sub_doc.id}: {str(e)}")
                            
                            if sample_docs:
                                collections_data[f"users/{user.id}/{sub_name}_samples"] = sample_docs
                except Exception as e:
                    debug_info.append(f"Error processing user subcollections for {user.id}: {str(e)}")
        
        return render_template("admin/backend_data.html", 
                               collections_data=collections_data, 
                               debug_info=debug_info)
        
    except Exception as e:
        logger.error(f"Backend data page error: {str(e)}")
        logger.error(traceback.format_exc())
        return render_template("admin/backend_data.html", 
                               error=str(e), 
                               debug_info=debug_info)


@app.route("/plans-diagnostic")
@admin_required
def plans_diagnostic():
    """
    Special diagnostic page just for PDF plans in the database.
    This helps identify issues with the PDF generation process.
    """
    debug_info = []
    all_plans = []
    users_with_plans = 0
    total_users = 0
    
    try:
        debug_info.append("Starting plans diagnostic route")
        
        # Use simple_initialize_firebase
        from services.firebase_service import simple_initialize_firebase, db
        
        debug_info.append("Imported Firebase services")
        
        if not simple_initialize_firebase():
            debug_info.append("Firebase initialization failed")
            flash('Error connecting to Firebase')
            return render_template("admin/plans_diagnostic.html", 
                                   error="Firebase connection failed", 
                                   debug_info=debug_info)

        debug_info.append("Firebase initialized successfully")
        
        # Get all users
        users_ref = db.collection('users')
        users = users_ref.stream()
        
        for user in users:
            total_users += 1
            try:
                user_data = user.to_dict()
                
                # Check for pdf_plans field
                if 'pdf_plans' not in user_data:
                    debug_info.append(f"User {user.id} has no pdf_plans field")
                    continue
                
                pdf_plans = user_data.get('pdf_plans', [])
                
                # Check if pdf_plans is a list
                if not isinstance(pdf_plans, list):
                    debug_info.append(f"User {user.id} has pdf_plans but it's not a list, it's a {type(pdf_plans)}")
                    continue
                
                # Check if pdf_plans is empty
                if not pdf_plans:
                    debug_info.append(f"User {user.id} has an empty pdf_plans list")
                    continue
                
                # User has plans
                users_with_plans += 1
                debug_info.append(f"User {user.id} has {len(pdf_plans)} plans")
                
                # Analyze each plan
                for i, plan in enumerate(pdf_plans):
                    try:
                        if not isinstance(plan, dict):
                            debug_info.append(f"  Plan {i} is not a dictionary, it's a {type(plan)}")
                            continue
                        
                        # Extract plan details
                        plan_info = {
                            'user_id': user.id,
                            'user_name': user_data.get('profile', {}).get('name', 'Unknown'),
                            'plan_index': i,
                        }
                        
                        # Check required fields
                        for field in ['filename', 'url', 'created_at']:
                            if field in plan:
                                plan_info[field] = plan[field]
                                if field == 'created_at' and hasattr(plan[field], 'seconds'):
                                    # Convert timestamp to datetime
                                    plan_info[f'{field}_formatted'] = datetime.datetime.fromtimestamp(plan[field].seconds)
                            else:
                                plan_info[field] = f"MISSING {field}"
                                debug_info.append(f"  Plan {i} is missing {field} field")
                        
                        # Add to all plans
                        all_plans.append(plan_info)
                        
                    except Exception as plan_error:
                        debug_info.append(f"  Error processing plan {i}: {str(plan_error)}")
                
            except Exception as user_error:
                debug_info.append(f"Error processing user {user.id}: {str(user_error)}")
        
        # Sort plans by created_at if available
        try:
            all_plans.sort(key=lambda x: x.get('created_at_formatted', datetime.datetime.min), reverse=True)
        except:
            debug_info.append("Error sorting plans by created_at")
        
        summary = {
            'total_users': total_users,
            'users_with_plans': users_with_plans,
            'total_plans': len(all_plans),
            'percentage_with_plans': round(users_with_plans / total_users * 100, 2) if total_users > 0 else 0
        }
        
        return render_template("admin/plans_diagnostic.html", 
                               plans=all_plans,
                               summary=summary,
                               debug_info=debug_info)
        
    except Exception as e:
        logger.error(f"Plans diagnostic page error: {str(e)}")
        logger.error(traceback.format_exc())
        return render_template("admin/plans_diagnostic.html", 
                               error=str(e), 
                               debug_info=debug_info)
    
@app.route("/debug-firebase")
def debug_firebase():
    debug_info = {
        'timestamp': datetime.datetime.now().isoformat(),
        'environment': {
            'FIREBASE_PROJECT_ID': os.getenv('FIREBASE_PROJECT_ID'),
            'FIREBASE_STORAGE_BUCKET': os.getenv('FIREBASE_STORAGE_BUCKET'),
            'GOOGLE_CLOUD_PROJECT': os.getenv('GOOGLE_CLOUD_PROJECT'),
            'K_SERVICE': os.getenv('K_SERVICE'),  # Will be set if running on Cloud Run
        },
        'initialization_steps': [],
        'errors': [],
        'final_status': 'not_started'
    }
    
    try:
        debug_info['initialization_steps'].append("Starting Firebase initialization")
        
        # Use simple_initialize_firebase for debugging
        from services.firebase_service import simple_initialize_firebase, db
        
        # Try to initialize Firebase
        debug_info['initialization_steps'].append("Attempting to initialize Firebase with simple_initialize_firebase")
        init_success = simple_initialize_firebase()
        if not init_success:
            debug_info['errors'].append("Firebase initialization returned False")
            debug_info['final_status'] = 'failed'
            return debug_info, 500
            
        debug_info['initialization_steps'].append("Firebase initialized successfully")
        
        # Try to access Firestore
        debug_info['initialization_steps'].append("Attempting to access Firestore")
        
        # Try to query admin_users collection
        debug_info['initialization_steps'].append("Attempting to query admin_users collection")
        admin_users = db.collection('admin_users').stream()
        users_found = []
        
        for admin in admin_users:
            admin_data = admin.to_dict()
            users_found.append({
                'id': admin.id,
                'username': admin_data.get('username'),
                'name': admin_data.get('name')
            })
        
        debug_info.update({
            'final_status': 'success',
            'firebase_apps': len(firebase_admin._apps),
            'users_found': users_found
        })
        
        return debug_info

    except Exception as e:
        import traceback
        debug_info['errors'].extend([
            f"Error type: {type(e).__name__}",
            f"Error message: {str(e)}",
            "Traceback:",
            traceback.format_exc()
        ])
        debug_info['final_status'] = 'error'
        return debug_info, 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting admin console on port {port}")
    app.run(debug=False, host="0.0.0.0", port=port)