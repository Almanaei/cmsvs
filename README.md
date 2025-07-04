# CMSVS Internal System

A comprehensive FastAPI + HTMX internal archival system with user authentication, file management, and admin dashboard.

## Features

### 🔐 Authentication System
- User registration and login
- JWT-based session management
- Password encryption with bcrypt
- Role-based access control (User/Admin)

### 👤 User Dashboard
- Personalized dashboard for each user
- Activity tracking and monitoring
- File management interface
- Request status monitoring

### 📁 File Upload System
- Maximum 5 files per request
- Automatic unique file naming
- File type validation (PDF, DOC, DOCX, TXT, JPG, JPEG, PNG, GIF)
- Maximum file size: 10MB per file
- Secure file storage management

### 📋 Archival Request System
- Request name and title (required fields)
- Auto-generated request number
- Auto-generated unique identification code
- Timestamp tracking
- Status tracking (Pending, In Progress, Completed, Rejected)

### 🛠️ Admin Dashboard
- User activity monitoring
- Request management and status updates
- System statistics and analytics
- File management oversight

## Technical Stack

### Backend
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - ORM for database operations
- **Pydantic** - Data validation and settings
- **JWT** - Authentication tokens
- **PostgreSQL** - Primary database

### Frontend
- **HTMX** - Dynamic HTML interactions
- **Jinja2** - Template engine
- **Tailwind CSS** - Utility-first CSS framework with RTL support
- **Alpine.js** - Lightweight JavaScript framework for interactive components

## 🎨 Modern UI with RTL Support

This project uses **HTMX** for dynamic interactions with **Tailwind CSS** providing a modern, responsive interface with full **RTL (Right-to-Left)** support for Arabic text and layouts.



## Installation

### Prerequisites
- Python 3.8+
- PostgreSQL 12+
- Node.js 16+ (for Tailwind CSS build)
- Git

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd cmsvs
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On Linux/Mac
   source venv/bin/activate
   ```

3. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Node.js dependencies and build CSS**
   ```bash
   npm install
   npm run build
   ```

5. **Setup PostgreSQL Database**
   ```sql
   CREATE DATABASE cmsvs_db;
   CREATE USER cmsvs_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE cmsvs_db TO cmsvs_user;
   ```

6. **Configure Environment Variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` file with your database credentials and settings:
   ```env
   DATABASE_URL=postgresql://cmsvs_user:your_password@localhost:5432/cmsvs_db
   SECRET_KEY=your-secret-key-here
   ADMIN_EMAIL=admin@company.com
   ADMIN_PASSWORD=admin123
   ```

7. **Run the application**
   ```bash
   python run.py
   ```

## Frontend Development

### CSS Development Workflow
For making style changes or customizations:

```bash
# Development mode (watch for changes)
npm run dev

# Production build (minified)
npm run build
```

### Tailwind CSS Features
- **RTL Support**: Full right-to-left layout support for Arabic
- **Responsive Design**: Mobile-first responsive components
- **Component Classes**: Pre-built components (buttons, cards, forms)
- **Utility Classes**: Comprehensive utility-first CSS framework

See `TAILWIND_SETUP.md` for detailed documentation.

## Usage

### First Time Setup

1. **Access the application**
   - Open your browser and go to `http://localhost:8000`
   - You'll be redirected to the login page

2. **Login as Admin**
   - Username: `admin`
   - Password: `admin123` (or your configured password)

3. **Change Admin Password**
   - Go to Profile settings and update your password
   - Update other admin details as needed

### For Regular Users

1. **Register Account**
   - Click "إنشاء حساب جديد" on login page
   - Fill in required information
   - Login with your credentials

2. **Create Requests**
   - Click "طلب جديد" from dashboard
   - Fill in request details
   - Upload files (optional, max 5 files)
   - Submit request

3. **Track Requests**
   - View all your requests from "طلباتي"
   - Check request status and details
   - Monitor request progress

### For Administrators

1. **Manage Users**
   - Access admin dashboard
   - View all users and their activities
   - Activate/deactivate user accounts

2. **Manage Requests**
   - View all system requests
   - Update request statuses
   - Filter requests by status
   - Monitor system statistics

## File Structure

```
cmsvs/
├── app/
│   ├── models/          # Database models
│   ├── routes/          # API routes
│   ├── services/        # Business logic
│   ├── templates/       # HTML templates
│   ├── utils/           # Utility functions
│   ├── config.py        # Configuration
│   ├── database.py      # Database setup
│   └── main.py          # FastAPI application
├── uploads/             # File storage
├── requirements.txt     # Python dependencies
├── .env.example        # Environment template
├── run.py              # Application runner
└── README.md           # This file
```

## API Endpoints

### Authentication
- `GET /login` - Login page
- `POST /login` - User login
- `GET /register` - Registration page
- `POST /register` - User registration
- `POST /logout` - User logout

### User Dashboard
- `GET /dashboard` - User dashboard
- `GET /requests` - List user requests
- `GET /requests/new` - New request form
- `POST /requests/new` - Create new request
- `GET /requests/{id}` - View request details

### Admin Dashboard
- `GET /admin/dashboard` - Admin dashboard
- `GET /admin/users` - Manage users
- `GET /admin/requests` - Manage requests
- `POST /admin/requests/{id}/update-status` - Update request status

## Security Features

- Password hashing with bcrypt
- JWT token authentication
- Role-based access control
- File type validation
- File size limits
- SQL injection protection
- XSS protection

## Configuration

Key configuration options in `.env`:

```env
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/db

# Security
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30

# File Upload
MAX_FILE_SIZE=10485760  # 10MB
ALLOWED_FILE_TYPES=pdf,doc,docx,txt,jpg,jpeg,png,gif

# Admin
ADMIN_EMAIL=admin@company.com
ADMIN_PASSWORD=admin123
```

## Deployment

### For LAN Network

1. **Update configuration**
   ```env
   DEBUG=False
   ```

2. **Run with production server**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

3. **Access from network**
   - Find server IP address
   - Access via `http://SERVER_IP:8000`

### Production Considerations

- Use HTTPS in production
- Set up proper database backups
- Configure log rotation
- Set up monitoring
- Use environment variables for secrets
- Consider using Docker for deployment

## Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Check PostgreSQL is running
   - Verify database credentials in `.env`
   - Ensure database exists

2. **File Upload Issues**
   - Check file permissions on upload directory
   - Verify file size and type restrictions
   - Ensure sufficient disk space

3. **Authentication Issues**
   - Check SECRET_KEY configuration
   - Verify token expiration settings
   - Clear browser cookies if needed

## Support

For support and questions:
- Check the logs for error details
- Verify configuration settings
- Ensure all dependencies are installed
- Check database connectivity

## License

This project is for internal use only.
