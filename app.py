from dotenv import load_dotenv
load_dotenv()
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from supabase_config import supabase
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from supabase import create_client

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'supersecretkey')

# --- Helper Functions ---
def is_logged_in():
    return 'user' in session

def get_user():
    return session.get('user')

# --- Routes ---
@app.route('/')
def home():
    if not is_logged_in():
        return redirect(url_for('login'))  # Redirect to login if not logged in
    user = get_user()
    # Fetch all users (id and name)
    users = supabase.table('users').select('id, name').execute().data
    user_dict = {u['id']: u['name'] for u in users if u.get('name')}
    # Fetch all artworks
    artworks = supabase.table('artworks').select('*').order('created_at', desc=True).execute().data
    filtered_artworks = []
    for art in artworks:
        # Get artist name, use user_id as fallback if name doesn't exist
        artist_name = user_dict.get(art['user_id'])
        if not artist_name:
            # Use first 8 characters of user_id as fallback
            artist_name = art['user_id'][:8] if art['user_id'] else 'Unknown Artist'
        art['user_name'] = artist_name
        # Count likes for each artwork
        art['like_count'] = len(supabase.table('likes').select('id').eq('artwork_id', art['id']).execute().data)
        # Fetch comments for each artwork
        comments = supabase.table('comments').select('*').eq('artwork_id', art['id']).order('created_at', desc=True).execute().data
        filtered_comments = []
        for comment in comments:
            name = user_dict.get(comment['user_id'])
            if not name:
                # Use first 8 characters of user_id as fallback
                name = comment['user_id'][:8] if comment['user_id'] else 'Unknown User'
            comment['user_name'] = name
            filtered_comments.append(comment)
        art['comments'] = filtered_comments
        # Check if current user liked this artwork
        liked = supabase.table('likes').select('id').eq('artwork_id', art['id']).eq('user_id', user['id']).execute().data
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
        try:
            res = supabase.auth.sign_up({"email": email, "password": password})
            if not res.user:
                flash('Registration failed: ' + str(res), 'danger')
                return redirect(url_for('register'))
            # Store name in session for use after login
            session['pending_name'] = name
            flash('Registration successful! Please check your email to confirm your account.', 'success')
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
            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
            user = res.user
            # Check if user exists in users table
            user_rows = supabase.table('users').select('name').eq('id', user.id).execute().data
            if not user_rows:
                # Use name from session if available
                name = session.pop('pending_name', '') if 'pending_name' in session else ''
                supabase.table('users').insert({
                    'id': user.id,
                    'name': name,
                    'email': user.email,
                    'created_at': datetime.utcnow().isoformat()
                }).execute()
                user_row = {'name': name}
            else:
                user_row = user_rows[0]
            session['user'] = {'id': user.id, 'email': user.email, 'name': user_row['name'] if user_row else ''}
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
    artworks = supabase.table('artworks').select('*').eq('user_id', user['id']).order('created_at', desc=True).execute().data
    # Fetch all users (id and name)
    users = supabase.table('users').select('id, name').execute().data
    user_dict = {u['id']: u['name'] for u in users}
    total_likes = 0
    total_comments = 0
    for art in artworks:
        # Attach artist name (optional, for consistency)
        art['user_name'] = user_dict.get(art['user_id'], art['user_id'][:8])
        # Count likes for each artwork
        art['like_count'] = len(supabase.table('likes').select('id').eq('artwork_id', art['id']).execute().data)
        total_likes += art['like_count']
        # Fetch comments for each artwork
        comments = supabase.table('comments').select('*').eq('artwork_id', art['id']).order('created_at', desc=True).execute().data
        for comment in comments:
            name = user_dict.get(comment['user_id'], '')
            comment['user_name'] = name if name else comment['user_id'][:8]
        art['comments'] = comments
        total_comments += len(comments)
        # Check if current user liked this artwork
        liked = supabase.table('likes').select('id').eq('artwork_id', art['id']).eq('user_id', user['id']).execute().data
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
            
            storage_path = f"artworks/{datetime.utcnow().timestamp()}_{filename}"
            
            # Check if Supabase is properly configured
            if not supabase.storage:
                flash('Storage service not available. Please check your configuration.', 'danger')
                return redirect(url_for('upload'))
            
            # Upload to Supabase storage with better error handling
            try:
                supabase.storage.from_('artwork-images').upload(storage_path, image.read(), {"content-type": image.mimetype})
            except Exception as storage_error:
                print(f"Storage upload error: {storage_error}")
                flash(f'Storage upload failed: {str(storage_error)}', 'danger')
                return redirect(url_for('upload'))
            
            # Get public URL
            try:
                image_url = supabase.storage.from_('artwork-images').get_public_url(storage_path)
            except Exception as url_error:
                print(f"URL generation error: {url_error}")
                flash(f'Failed to generate image URL: {str(url_error)}', 'danger')
                return redirect(url_for('upload'))
            
            user = get_user()
            
            # Insert into database
            try:
                supabase.table('artworks').insert({
                    'user_id': user['id'],
                    'title': title,
                    'description': description,
                    'image_url': image_url,
                    'created_at': datetime.utcnow().isoformat()
                }).execute()
            except Exception as db_error:
                print(f"Database insert error: {db_error}")
                flash(f'Failed to save artwork to database: {str(db_error)}', 'danger')
                return redirect(url_for('upload'))
            
            flash('Artwork uploaded successfully!', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            print(f"Upload error: {e}")
            flash(f'Upload failed: {str(e)}', 'danger')
            return redirect(url_for('upload'))
    
    return render_template('upload.html')

@app.route('/gallery')
def gallery():
    artworks = supabase.table('artworks').select('*').order('created_at', desc=True).execute().data
    for art in artworks:
        art['like_count'] = len(supabase.table('likes').select('id').eq('artwork_id', art['id']).execute().data)
        art['comment_count'] = len(supabase.table('comments').select('id').eq('artwork_id', art['id']).execute().data)
    return render_template('gallery.html', artworks=artworks, user=get_user())

@app.route('/like/<artwork_id>', methods=['POST'])
def like_artwork(artwork_id):
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Login required'}), 401
    user = get_user()
    # Prevent duplicate likes
    existing = supabase.table('likes').select('*').eq('user_id', user['id']).eq('artwork_id', artwork_id).execute().data
    if existing:
        return jsonify({'success': False, 'message': 'Already liked'}), 400
    supabase.table('likes').insert({
        'user_id': user['id'],
        'artwork_id': artwork_id,
        'created_at': datetime.utcnow().isoformat()
    }).execute()
    return jsonify({'success': True})

@app.route('/comment/<artwork_id>', methods=['POST'])
def comment_artwork(artwork_id):
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Login required'}), 401
    user = get_user()
    content = request.form['content']
    if not content:
        return jsonify({'success': False, 'message': 'Comment required'}), 400
    supabase.table('comments').insert({
        'user_id': user['id'],
        'artwork_id': artwork_id,
        'content': content,
        'created_at': datetime.utcnow().isoformat()
    }).execute()
    return jsonify({'success': True})

@app.route('/profile')
def profile():
    if not is_logged_in():
        return redirect(url_for('login'))
    user = get_user()
    user_data = supabase.table('users').select('*').eq('id', user['id']).single().execute().data
    return render_template('profile.html', user=user_data)

# --- API Endpoints for AJAX ---
@app.route('/api/artworks/<artwork_id>/likes')
def api_artwork_likes(artwork_id):
    count = len(supabase.table('likes').select('id').eq('artwork_id', artwork_id).execute().data)
    return jsonify({'count': count})

@app.route('/api/artworks/<artwork_id>/comments')
def api_artwork_comments(artwork_id):
    comments = supabase.table('comments').select('*').eq('artwork_id', artwork_id).order('created_at', desc=True).execute().data
    # Fetch all users (id and name)
    users = supabase.table('users').select('id, name').execute().data
    user_dict = {u['id']: u['name'] for u in users}
    for comment in comments:
        name = user_dict.get(comment['user_id'], '')
        comment['user_name'] = name if name else comment['user_id'][:8]
    return jsonify({'comments': comments})

# --- Debug Routes ---
@app.route('/debug/supabase')
def debug_supabase():
    if not is_logged_in():
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        # Test basic Supabase connection
        test_result = supabase.table('users').select('count').limit(1).execute()
        
        # Test storage access
        storage_test = None
        try:
            # Try to list storage buckets
            buckets = supabase.storage.list_buckets()
            storage_test = f"Storage accessible. Buckets: {len(buckets)}"
        except Exception as e:
            storage_test = f"Storage error: {str(e)}"
        
        return jsonify({
            'supabase_configured': True,
            'database_accessible': True,
            'storage_status': storage_test,
            'user_id': get_user()['id']
        })
    except Exception as e:
        return jsonify({
            'supabase_configured': False,
            'error': str(e)
        })

if __name__ == '__main__':
    app.run(debug=True) 