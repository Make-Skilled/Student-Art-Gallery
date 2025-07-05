from dotenv import load_dotenv
load_dotenv()
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from mongodb_config import (
    users_collection, artworks_collection, likes_collection, comments_collection,
    hash_password, verify_password, generate_token, verify_token,
    get_user_by_id, get_user_by_email, create_user, save_file_to_db, get_file_from_db
)
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from bson import ObjectId
import io

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'supersecretkey')

# --- Helper Functions ---
def is_logged_in():
    return 'user' in session

def get_user():
    return session.get('user')

def get_user_by_token():
    """Get user from JWT token in request headers"""
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        user_id = verify_token(token)
        if user_id:
            return get_user_by_id(user_id)
    return None

# --- Routes ---
@app.route('/')
def home():
    if not is_logged_in():
        return redirect(url_for('login'))
    
    user = get_user()
    
    # Fetch all users (id and name)
    users = list(users_collection.find({}, {'_id': 1, 'name': 1}))
    user_dict = {str(u['_id']): u.get('name', '') for u in users}
    
    # Fetch all artworks
    artworks = list(artworks_collection.find().sort('created_at', -1))
    filtered_artworks = []
    
    for art in artworks:
        # Convert ObjectId to string for JSON serialization
        art['_id'] = str(art['_id'])
        art['user_id'] = str(art['user_id'])
        
        # Get artist name
        artist_name = user_dict.get(art['user_id'])
        if not artist_name:
            artist_name = art['user_id'][:8] if art['user_id'] else 'Unknown Artist'
        art['user_name'] = artist_name
        
        # Count likes for each artwork
        like_count = likes_collection.count_documents({'artwork_id': art['_id']})
        art['like_count'] = like_count
        
        # Fetch comments for each artwork
        comments = list(comments_collection.find({'artwork_id': art['_id']}).sort('created_at', -1))
        filtered_comments = []
        for comment in comments:
            comment['_id'] = str(comment['_id'])
            comment['user_id'] = str(comment['user_id'])
            name = user_dict.get(comment['user_id'])
            if not name:
                name = comment['user_id'][:8] if comment['user_id'] else 'Unknown User'
            comment['user_name'] = name
            filtered_comments.append(comment)
        art['comments'] = filtered_comments
        
        # Check if current user liked this artwork
        liked = likes_collection.find_one({'artwork_id': art['_id'], 'user_id': ObjectId(user['id'])})
        art['liked_by_user'] = bool(liked)
        filtered_artworks.append(art)
    
    return render_template('home.html', artworks=filtered_artworks, user=user)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        if not name or not email or not password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('register'))
        
        # Check if user already exists
        existing_user = get_user_by_email(email)
        if existing_user:
            flash('User with this email already exists.', 'danger')
            return redirect(url_for('register'))
        
        try:
            # Create user
            user_data = {
                'name': name,
                'email': email,
                'password': password  # Will be hashed in create_user function
            }
            user_id = create_user(user_data)
            
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Registration failed: {e}', 'danger')
            return redirect(url_for('register'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        if not email or not password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('login'))
        
        try:
            # Find user by email
            user = get_user_by_email(email)
            if not user:
                flash('Invalid email or password.', 'danger')
                return redirect(url_for('login'))
            
            # Verify password
            if not verify_password(password, user['password']):
                flash('Invalid email or password.', 'danger')
                return redirect(url_for('login'))
            
            # Store user in session
            session['user'] = {
                'id': str(user['_id']),
                'email': user['email'],
                'name': user.get('name', '')
            }
            session.permanent = True
            
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        except Exception as e:
            flash(f'Login failed: {e}', 'danger')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if not is_logged_in():
        return redirect(url_for('login'))
    
    user = get_user()
    
    # Only fetch artworks uploaded by the logged-in user
    artworks = list(artworks_collection.find({'user_id': ObjectId(user['id'])}).sort('created_at', -1))
    
    # Fetch all users (id and name)
    users = list(users_collection.find({}, {'_id': 1, 'name': 1}))
    user_dict = {str(u['_id']): u.get('name', '') for u in users}
    
    total_likes = 0
    total_comments = 0
    
    for art in artworks:
        # Convert ObjectId to string
        art['_id'] = str(art['_id'])
        art['user_id'] = str(art['user_id'])
        
        # Attach artist name
        art['user_name'] = user_dict.get(art['user_id'], art['user_id'][:8])
        
        # Count likes for each artwork
        like_count = likes_collection.count_documents({'artwork_id': art['_id']})
        art['like_count'] = like_count
        total_likes += like_count
        
        # Fetch comments for each artwork
        comments = list(comments_collection.find({'artwork_id': art['_id']}).sort('created_at', -1))
        for comment in comments:
            comment['_id'] = str(comment['_id'])
            comment['user_id'] = str(comment['user_id'])
            name = user_dict.get(comment['user_id'], '')
            comment['user_name'] = name if name else comment['user_id'][:8]
        art['comments'] = comments
        total_comments += len(comments)
        
        # Check if current user liked this artwork
        liked = likes_collection.find_one({'artwork_id': art['_id'], 'user_id': ObjectId(user['id'])})
        art['liked_by_user'] = bool(liked)
    
    return render_template('dashboard.html', user=user, artworks=artworks, total_likes=total_likes, total_comments=total_comments)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if not is_logged_in():
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        image = request.files['image']
        
        if not title or not description or not image:
            flash('All fields are required.', 'danger')
            return redirect(url_for('upload'))
        
        # Validate file type
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        if not image.filename or '.' not in image.filename:
            flash('Please select a valid image file.', 'danger')
            return redirect(url_for('upload'))
        
        file_extension = image.filename.rsplit('.', 1)[1].lower()
        if file_extension not in allowed_extensions:
            flash('Please select a valid image file (PNG, JPG, JPEG, GIF, WEBP).', 'danger')
            return redirect(url_for('upload'))
        
        filename = secure_filename(image.filename)
        
        try:
            # Reset file pointer to beginning
            image.seek(0)
            file_data = image.read()
            
            # Save file to MongoDB using GridFS
            file_id = save_file_to_db(file_data, filename, image.content_type)
            print(f"File saved with ID: {file_id}")
            
            user = get_user()
            
            # Insert artwork into database
            artwork_data = {
                'user_id': ObjectId(user['id']),
                'title': title,
                'description': description,
                'file_id': file_id,
                'filename': filename,
                'content_type': image.content_type,
                'created_at': datetime.utcnow()
            }
            
            result = artworks_collection.insert_one(artwork_data)
            print(f"Artwork saved with ID: {result.inserted_id}")
            
            flash('Artwork uploaded successfully!', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            print(f"Upload error: {e}")
            flash(f'Upload failed: {str(e)}', 'danger')
            return redirect(url_for('upload'))
    
    return render_template('upload.html')

@app.route('/image/<file_id>')
def serve_image(file_id):
    """Serve image from MongoDB GridFS"""
    try:
        print(f"Attempting to serve image with file_id: {file_id}")
        file_obj = get_file_from_db(file_id)
        if file_obj:
            print(f"File found: {file_obj.filename}, content_type: {file_obj.content_type}")
            return send_file(
                io.BytesIO(file_obj.read()),
                mimetype=file_obj.content_type,
                as_attachment=False,
                download_name=file_obj.filename
            )
        else:
            print(f"File not found for file_id: {file_id}")
            return "Image not found", 404
    except Exception as e:
        print(f"Error serving image: {str(e)}")
        return f"Error serving image: {str(e)}", 500

@app.route('/gallery')
def gallery():
    artworks = list(artworks_collection.find().sort('created_at', -1))
    
    for art in artworks:
        art['_id'] = str(art['_id'])
        art['user_id'] = str(art['user_id'])
        art['like_count'] = likes_collection.count_documents({'artwork_id': art['_id']})
        art['comment_count'] = comments_collection.count_documents({'artwork_id': art['_id']})
    
    return render_template('gallery.html', artworks=artworks, user=get_user())

@app.route('/like/<artwork_id>', methods=['POST'])
def like_artwork(artwork_id):
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Login required'}), 401
    
    user = get_user()
    
    # Prevent duplicate likes
    existing = likes_collection.find_one({'user_id': ObjectId(user['id']), 'artwork_id': artwork_id})
    if existing:
        return jsonify({'success': False, 'message': 'Already liked'}), 400
    
    likes_collection.insert_one({
        'user_id': ObjectId(user['id']),
        'artwork_id': artwork_id,
        'created_at': datetime.utcnow()
    })
    
    return jsonify({'success': True})

@app.route('/comment/<artwork_id>', methods=['POST'])
def comment_artwork(artwork_id):
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Login required'}), 401
    
    user = get_user()
    content = request.form['content']
    
    if not content:
        return jsonify({'success': False, 'message': 'Comment required'}), 400
    
    comments_collection.insert_one({
        'user_id': ObjectId(user['id']),
        'artwork_id': artwork_id,
        'content': content,
        'created_at': datetime.utcnow()
    })
    
    return jsonify({'success': True})

@app.route('/profile')
def profile():
    if not is_logged_in():
        return redirect(url_for('login'))
    
    user = get_user()
    user_data = get_user_by_id(user['id'])
    
    if user_data:
        user_data['_id'] = str(user_data['_id'])
        # Remove password from user data
        user_data.pop('password', None)
    else:
        # If user data not found in database, use session data
        user_data = {
            '_id': user['id'],
            'name': user.get('name', ''),
            'email': user.get('email', ''),
            'created_at': datetime.utcnow()
        }
    
    return render_template('profile.html', user=user_data)

# --- API Endpoints for AJAX ---
@app.route('/api/artworks/<artwork_id>/likes')
def api_artwork_likes(artwork_id):
    count = likes_collection.count_documents({'artwork_id': artwork_id})
    return jsonify({'count': count})

@app.route('/api/artworks/<artwork_id>/comments')
def api_artwork_comments(artwork_id):
    comments = list(comments_collection.find({'artwork_id': artwork_id}).sort('created_at', -1))
    
    # Fetch all users (id and name)
    users = list(users_collection.find({}, {'_id': 1, 'name': 1}))
    user_dict = {str(u['_id']): u.get('name', '') for u in users}
    
    for comment in comments:
        comment['_id'] = str(comment['_id'])
        comment['user_id'] = str(comment['user_id'])
        name = user_dict.get(comment['user_id'], '')
        comment['user_name'] = name if name else comment['user_id'][:8]
    
    return jsonify({'comments': comments})

# --- Debug Routes ---
@app.route('/debug/mongodb')
def debug_mongodb():
    if not is_logged_in():
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        # Test basic MongoDB connection
        user_count = users_collection.count_documents({})
        artwork_count = artworks_collection.count_documents({})
        
        return jsonify({
            'mongodb_configured': True,
            'database_accessible': True,
            'user_count': user_count,
            'artwork_count': artwork_count,
            'user_id': get_user()['id']
        })
    except Exception as e:
        return jsonify({
            'mongodb_configured': False,
            'error': str(e)
        })

if __name__ == '__main__':
    app.run(debug=True) 