from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, flash, current_app
from werkzeug.utils import secure_filename
import os
import PyPDF2
import io
from datetime import datetime
import logging
from database import DatabaseManager

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, template_folder='templates')
db = DatabaseManager()

# PDF upload configuration
ALLOWED_EXTENSIONS = {'pdf'}
UPLOAD_FOLDER = 'uploads'
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@admin_bp.route('/')
def index():
    """Redirect to login if not authenticated"""
    if 'admin_id' not in session:
        return redirect(url_for('admin.login'))
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Debug logging
        logger.info(f"Login attempt - Username: {username}")
        
        user = db.get_user_by_username(username)
        
        if user:
            logger.info(f"User found: {user}")
            if user[4] == 'admin' and user[3] == password:  # Simple password check
                session['admin_id'] = user[0]
                session['admin_username'] = user[1]
                db.update_last_login(user[0])
                db.log_admin_action(user[0], 'login', f'Admin {username} logged in')
                logger.info(f"Login successful for {username}")
                return redirect(url_for('admin.dashboard'))
            else:
                logger.warning(f"Invalid credentials for {username}")
                flash('Invalid username or password', 'error')
        else:
            logger.warning(f"User not found: {username}")
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@admin_bp.route('/logout')
def logout():
    """Admin logout"""
    if 'admin_id' in session:
        db.log_admin_action(session['admin_id'], 'logout', 'Admin logged out')
        session.clear()
    return redirect(url_for('admin.login'))

@admin_bp.route('/dashboard')
def dashboard():
    """Admin dashboard"""
    if 'admin_id' not in session:
        return redirect(url_for('admin.login'))
    
    stats = {
        'total_users': len(db.get_all_users()),
        'total_chats': len(db.get_chat_history()),
        'total_pdfs': len(db.get_pdf_uploads()),
        'recent_logs': db.get_admin_logs(limit=10)
    }
    
    return render_template('dashboard.html', stats=stats)

@admin_bp.route('/upload-pdf', methods=['GET', 'POST'])
def upload_pdf():
    """PDF upload functionality"""
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    if request.method == 'POST':
        try:
            if 'file' not in request.files:
                return jsonify({'error': 'No file selected'}), 400
            
            file = request.files['file']
            category = request.form.get('category', 'general')
            tags = request.form.get('tags', '')
            description = request.form.get('description', '')
            
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            
            if file and allowed_file(file.filename):
                # Create uploads directory if not exists
                if not os.path.exists(UPLOAD_FOLDER):
                    os.makedirs(UPLOAD_FOLDER)
                
                # Save file
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{timestamp}_{filename}"
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)
                
                # Get file size
                file_size = os.path.getsize(filepath)
                
                # Save to database
                pdf_id = db.save_pdf_upload(
                    filename, file.filename, category, tags, description, 
                    file_size, session['admin_id']
                )
                
                if pdf_id:
                    # Extract and save PDF content
                    try:
                        with open(filepath, 'rb') as pdf_file:
                            pdf_reader = PyPDF2.PdfReader(pdf_file)
                            
                            for page_num in range(len(pdf_reader.pages)):
                                page = pdf_reader.pages[page_num]
                                content = page.extract_text()
                                
                                # Extract keywords (simple approach)
                                keywords = ' '.join([word.lower() for word in content.split() if len(word) > 3])
                                
                                db.save_pdf_content(pdf_id, page_num + 1, content, keywords)
                    
                    except Exception as e:
                        logger.error(f"Error extracting PDF content: {e}")
                    
                    # Log action
                    db.log_admin_action(session['admin_id'], 'upload_pdf', f'Uploaded PDF: {file.filename}')
                    
                    return jsonify({
                        'success': True,
                        'message': 'PDF uploaded successfully',
                        'pdf_id': pdf_id
                    })
                else:
                    # Remove file if database save failed
                    os.remove(filepath)
                    return jsonify({'error': 'Failed to save PDF information'}), 500
            else:
                return jsonify({'error': 'Invalid file type. Only PDF files are allowed'}), 400
                
        except Exception as e:
            logger.error(f"Error uploading PDF: {e}")
            return jsonify({'error': 'Failed to upload PDF'}), 500
    
    return render_template('upload_pdf.html')

@admin_bp.route('/manage-pdfs')
def manage_pdfs():
    """Manage uploaded PDFs"""
    if 'admin_id' not in session:
        return redirect(url_for('admin.login'))
    
    category = request.args.get('category')
    pdfs = db.get_pdf_uploads(category)
    
    return render_template('manage_pdfs.html', pdfs=pdfs, selected_category=category)

@admin_bp.route('/delete-pdf/<int:pdf_id>', methods=['POST'])
def delete_pdf(pdf_id):
    """Delete a PDF"""
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # Get PDF info for logging
        pdfs = db.get_pdf_uploads()
        pdf_info = next((pdf for pdf in pdfs if pdf[0] == pdf_id), None)
        
        if pdf_info:
            # Delete from database
            if db.delete_pdf(pdf_id):
                # Delete physical file
                filepath = os.path.join(UPLOAD_FOLDER, pdf_info[1])
                if os.path.exists(filepath):
                    os.remove(filepath)
                
                # Log action
                db.log_admin_action(session['admin_id'], 'delete_pdf', f'Deleted PDF: {pdf_info[2]}')
                
                return jsonify({'success': True, 'message': 'PDF deleted successfully'})
            else:
                return jsonify({'error': 'Failed to delete PDF'}), 500
        else:
            return jsonify({'error': 'PDF not found'}), 404
            
    except Exception as e:
        logger.error(f"Error deleting PDF: {e}")
        return jsonify({'error': 'Failed to delete PDF'}), 500

@admin_bp.route('/api/search-pdfs')
def search_pdfs():
    """Search PDFs API"""
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    query = request.args.get('q', '')
    if not query:
        return jsonify({'error': 'No query provided'}), 400
    
    try:
        results = db.search_pdf_content(query)
        return jsonify({'results': results})
    except Exception as e:
        logger.error(f"Error searching PDFs: {e}")
        return jsonify({'error': 'Search failed'}), 500

@admin_bp.route('/api/scraping-status')
def api_scraping_status():
    """Get scraping status"""
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # Get last scraping data
        scraped_data = db.get_scraped_data()
        last_updated = None
        
        if scraped_data:
            # Get the most recent timestamp from scraped data
            last_updated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return jsonify({
            'status': 'success',
            'last_updated': last_updated,
            'data_available': bool(scraped_data),
            'categories': list(scraped_data.keys()) if scraped_data else []
        })
    except Exception as e:
        logger.error(f"Error getting scraping status: {e}")
        return jsonify({'error': 'Failed to get scraping status'}), 500

@admin_bp.route('/api/scrape-all', methods=['POST'])
def api_scrape_all():
    """Trigger full scraping"""
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        from scraper import VBSPUScraper
        scraper = VBSPUScraper()
        data = scraper.scrape_all()
        
        # Save to database
        for category, content in data.items():
            db.save_scraped_data(category, content)
        
        db.log_admin_action(session['admin_id'], 'scrape_all', 'Full scraping triggered')
        return jsonify({
            'status': 'success',
            'message': 'Scraping completed successfully',
            'data': data
        })
    except Exception as e:
        logger.error(f"Error in full scraping: {e}")
        return jsonify({'error': 'Scraping failed'}), 500

@admin_bp.route('/api/add-user', methods=['POST'])
def api_add_user():
    """Add new user"""
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        role = data.get('role', 'user')
        
        # Validate input
        if not username or not email or not password or not role:
            return jsonify({'error': 'All fields are required'}), 400
        
        # Check if username already exists
        existing_user = db.get_user_by_username(username)
        if existing_user:
            return jsonify({'error': 'Username already exists'}), 400
        
        # Create user (simplified - in production, hash the password)
        user_id = db.create_user(username, email, password, role)
        
        if user_id:
            db.log_admin_action(session['admin_id'], 'add_user', f'Created user: {username}')
            return jsonify({
                'success': True,
                'message': 'User created successfully',
                'user_id': user_id
            })
        else:
            return jsonify({'error': 'Failed to create user'}), 500
    except Exception as e:
        logger.error(f"Error adding user: {e}")
        return jsonify({'error': 'Failed to create user'}), 500

@admin_bp.route('/api/users/<int:user_id>', methods=['GET'])
def api_get_user(user_id):
    """Get single user"""
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        user = db.get_user_by_id(user_id)
        if user:
            return jsonify({
                'id': user[0],
                'username': user[1],
                'email': user[2],
                'role': user[4],
                'created_at': user[5],
                'last_login': user[6]
            })
        else:
            return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        return jsonify({'error': 'Failed to get user'}), 500

@admin_bp.route('/api/users/<int:user_id>', methods=['PUT'])
def api_update_user(user_id):
    """Update user"""
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        role = data.get('role')
        
        # Validate input
        if not username or not role:
            return jsonify({'error': 'Username and role are required'}), 400
        
        # Update user
        success = db.update_user(user_id, username, email, password, role)
        
        if success:
            db.log_admin_action(session['admin_id'], 'update_user', f'Updated user ID: {user_id}')
            return jsonify({
                'success': True,
                'message': 'User updated successfully'
            })
        else:
            return jsonify({'error': 'Failed to update user'}), 500
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        return jsonify({'error': 'Failed to update user'}), 500

@admin_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
def api_delete_user(user_id):
    """Delete user"""
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # Don't allow admin to delete themselves
        if user_id == session['admin_id']:
            return jsonify({'error': 'Cannot delete admin account'}), 400
        
        # Delete user
        success = db.delete_user(user_id)
        
        if success:
            db.log_admin_action(session['admin_id'], 'delete_user', f'Deleted user ID: {user_id}')
            return jsonify({
                'success': True,
                'message': 'User deleted successfully'
            })
        else:
            return jsonify({'error': 'Failed to delete user'}), 500
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        return jsonify({'error': 'Failed to delete user'}), 500

@admin_bp.route('/add-user')
def add_user():
    """Add user page"""
    if 'admin_id' not in session:
        return redirect(url_for('admin.login'))
    return render_template('add_user.html')

@admin_bp.route('/edit-user/<int:user_id>')
def edit_user(user_id):
    """Edit user page"""
    if 'admin_id' not in session:
        return redirect(url_for('admin.login'))
    return render_template('edit_user.html', user_id=user_id)

# API Routes
@admin_bp.route('/api/dashboard')
def api_dashboard():
    """Get dashboard statistics"""
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # Get statistics
        users = db.get_all_users()
        chats = db.get_chat_history()
        pdfs = db.get_pdf_uploads()
        logs = db.get_admin_logs(limit=10)
        
        # Get last scraping data
        scraped_data = db.get_scraped_data()
        last_updated = None
        if scraped_data:
            last_updated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        stats = {
            'total_users': len(users),
            'total_chats': len(chats),
            'total_pdfs': len(pdfs),
            'data_last_updated': last_updated or 'Never',
            'bot_status': 'Active',
            'recent_logs': logs
        }
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        return jsonify({'error': 'Failed to get stats'}), 500

@admin_bp.route('/api/scrape', methods=['POST'])
def api_scrape():
    """Manual scraping trigger"""
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        from scraper import VBSPUScraper
        scraper = VBSPUScraper()
        data = scraper.scrape_all()
        
        # Save to database
        for category, content in data.items():
            db.save_scraped_data(category, content)
        
        db.log_admin_action(session['admin_id'], 'scrape', 'Manual scraping triggered')
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"Error scraping: {e}")
        return jsonify({'error': 'Scraping failed'}), 500

@admin_bp.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    """Bot settings management"""
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            for key, value in data.items():
                db.update_setting(key, value)
            
            db.log_admin_action(session['admin_id'], 'update_settings', 'Updated bot settings')
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"Error updating settings: {e}")
            return jsonify({'error': 'Failed to update settings'}), 500
    else:
        try:
            settings = db.get_all_settings()
            return jsonify(settings)
        except Exception as e:
            logger.error(f"Error getting settings: {e}")
            return jsonify({'error': 'Failed to get settings'}), 500

@admin_bp.route('/api/users')
def api_users():
    """Get users list"""
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        users = db.get_all_users()
        return jsonify(users)
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        return jsonify({'error': 'Failed to get users'}), 500

@admin_bp.route('/api/logs')
def api_logs():
    """Get admin logs"""
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        limit = request.args.get('limit', 50, type=int)
        logs = db.get_admin_logs(limit=limit)
        return jsonify(logs)
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        return jsonify({'error': 'Failed to get logs'}), 500

@admin_bp.route('/api/chat-history')
def api_chat_history():
    """Get chat history"""
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        limit = request.args.get('limit', 100, type=int)
        history = db.get_chat_history(limit=limit)
        return jsonify(history)
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        return jsonify({'error': 'Failed to get chat history'}), 500
