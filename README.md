# Student Art Gallery - MongoDB Atlas Version

A Flask-based art gallery application where students can upload, share, and interact with artwork. This version uses MongoDB Atlas for data storage and GridFS for file storage.

## Features

- User registration and authentication
- Artwork upload with file storage in MongoDB GridFS
- Like and comment functionality
- User dashboard with personal artwork management
- Public gallery view
- Responsive design

## Setup Instructions

### 1. MongoDB Atlas Setup

1. Create a MongoDB Atlas account at [https://www.mongodb.com/atlas](https://www.mongodb.com/atlas)
2. Create a new cluster (free tier is sufficient)
3. Create a database user with read/write permissions
4. Get your connection string from the cluster dashboard
5. Add your IP address to the IP whitelist

### 2. Environment Configuration

1. Copy `env_example.txt` to `.env`
2. Update the following variables in your `.env` file:

```env
MONGODB_URI=mongodb+srv://your_username:your_password@your_cluster.mongodb.net/student_art_gallery?retryWrites=true&w=majority
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production
SECRET_KEY=your-flask-secret-key-change-this-in-production
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Application

```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Database Schema

The application uses the following MongoDB collections:

- **users**: User accounts with authentication data
- **artworks**: Artwork metadata and file references
- **likes**: User likes on artworks
- **comments**: User comments on artworks
- **fs.files** and **fs.chunks**: GridFS collections for file storage

## File Storage

All uploaded images are stored directly in MongoDB using GridFS, eliminating the need for local file storage or external cloud storage services.

## API Endpoints

- `GET /`: Home page with art feed
- `GET /register`: User registration page
- `POST /register`: User registration
- `GET /login`: Login page
- `POST /login`: User login
- `GET /logout`: User logout
- `GET /dashboard`: User dashboard
- `GET /upload`: Artwork upload page
- `POST /upload`: Artwork upload
- `GET /gallery`: Public gallery
- `POST /like/<artwork_id>`: Like an artwork
- `POST /comment/<artwork_id>`: Comment on an artwork
- `GET /image/<file_id>`: Serve image from GridFS
- `GET /profile`: User profile page

## Security Features

- Password hashing using bcrypt
- JWT token-based authentication
- Secure file upload validation
- Session management

## Migration from Supabase

This version has been migrated from Supabase to MongoDB Atlas. Key changes:

- Replaced Supabase client with PyMongo
- Implemented custom authentication using bcrypt and JWT
- Added GridFS for file storage
- Updated all database queries to use MongoDB syntax
- Modified templates to use new image serving endpoints

## Troubleshooting

1. **Connection Issues**: Ensure your MongoDB Atlas connection string is correct and your IP is whitelisted
2. **File Upload Issues**: Check that GridFS is properly configured and the database has sufficient storage
3. **Authentication Issues**: Verify JWT_SECRET is set and consistent

## Development

To run in development mode:

```bash
export FLASK_ENV=development
python app.py
```

Debug information is available at `/debug/mongodb` when logged in. 