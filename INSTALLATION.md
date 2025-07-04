# CMSVS Internal System - Installation Guide

## Quick Start (Windows)

### Option 1: Automatic Setup (Recommended)
1. **Download and extract the project**
2. **Double-click `start.bat`** - This will automatically:
   - Create virtual environment
   - Install dependencies
   - Copy configuration file
   - Start the application

### Option 2: Manual Setup
1. **Open Command Prompt or PowerShell**
2. **Navigate to project directory**
   ```cmd
   cd path\to\cmsvs
   ```
3. **Run the setup commands**
   ```cmd
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   copy .env.example .env
   ```

## Quick Start (Linux/Mac)

### Option 1: Automatic Setup (Recommended)
1. **Download and extract the project**
2. **Run the startup script**
   ```bash
   chmod +x start.sh
   ./start.sh
   ```

### Option 2: Manual Setup
1. **Open Terminal**
2. **Navigate to project directory**
   ```bash
   cd path/to/cmsvs
   ```
3. **Run the setup commands**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   ```

## Database Setup

### PostgreSQL Installation

#### Windows
1. Download PostgreSQL from https://www.postgresql.org/download/windows/
2. Install with default settings
3. Remember the password you set for the `postgres` user

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

#### Mac
```bash
brew install postgresql
brew services start postgresql
```

### Database Configuration

1. **Connect to PostgreSQL**
   ```sql
   -- Windows: Use pgAdmin or psql
   -- Linux/Mac: 
   sudo -u postgres psql
   ```

2. **Create database and user**
   ```sql
   CREATE DATABASE cmsvs_db;
   CREATE USER cmsvs_user WITH PASSWORD 'your_secure_password';
   GRANT ALL PRIVILEGES ON DATABASE cmsvs_db TO cmsvs_user;
   \q
   ```

3. **Update .env file**
   ```env
   DATABASE_URL=postgresql://cmsvs_user:your_secure_password@localhost:5432/cmsvs_db
   SECRET_KEY=your-very-secure-secret-key-change-this
   ADMIN_EMAIL=admin@yourcompany.com
   ADMIN_PASSWORD=change_this_password
   ```

## Application Setup

1. **Initialize the database**
   ```bash
   python init_db.py
   ```

2. **Start the application**
   ```bash
   python run.py
   ```

3. **Access the application**
   - Open browser: http://localhost:8000
   - Login with admin credentials from .env file

## Docker Setup (Alternative)

If you prefer Docker:

1. **Install Docker and Docker Compose**

2. **Update docker-compose.yml** with your settings

3. **Start the services**
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   - Application: http://localhost:8000
   - Database: localhost:5432

## Troubleshooting

### Common Issues

#### 1. "No module named 'pydantic_settings'"
**Solution:** Install dependencies
```bash
pip install -r requirements.txt
```

#### 2. "psycopg2 installation failed"
**Windows Solution:**
```bash
pip install psycopg2-binary
```

**Linux Solution:**
```bash
sudo apt-get install libpq-dev python3-dev
pip install psycopg2
```

#### 3. "Database connection failed"
- Check if PostgreSQL is running
- Verify database credentials in .env
- Ensure database exists

#### 4. "Permission denied" on Linux/Mac
```bash
chmod +x start.sh
chmod +x init_db.py
```

#### 5. "Port 8000 already in use"
Edit `run.py` and change the port:
```python
uvicorn.run("app.main:app", host="0.0.0.0", port=8001)
```

### Testing the Setup

Run the test script to verify everything is working:
```bash
python test_setup.py
```

## Network Access (LAN Deployment)

To access from other computers on your network:

1. **Find your IP address**
   ```bash
   # Windows
   ipconfig
   
   # Linux/Mac
   ifconfig
   ```

2. **Update firewall settings** (if needed)
   - Windows: Allow Python through Windows Firewall
   - Linux: `sudo ufw allow 8000`

3. **Access from other computers**
   - URL: http://YOUR_IP_ADDRESS:8000

## Production Deployment

For production use:

1. **Update .env file**
   ```env
   DEBUG=False
   SECRET_KEY=very-secure-random-key
   ```

2. **Use a production WSGI server**
   ```bash
   pip install gunicorn
   gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
   ```

3. **Set up reverse proxy** (nginx/Apache)

4. **Enable HTTPS**

5. **Set up database backups**

## Default Credentials

**Admin Account:**
- Username: `admin`
- Password: (as set in .env file, default: `admin123`)

**Important:** Change the admin password after first login!

## Support

If you encounter issues:

1. Check the logs in the terminal
2. Verify all dependencies are installed
3. Ensure PostgreSQL is running
4. Check database connection settings
5. Run `python test_setup.py` for diagnostics

## File Structure Overview

```
cmsvs/
├── app/                    # Main application
│   ├── models/            # Database models
│   ├── routes/            # API endpoints
│   ├── services/          # Business logic
│   ├── templates/         # HTML templates
│   ├── utils/             # Utilities
│   └── static/            # Static files directory
├── uploads/               # File storage (created automatically)
├── requirements.txt       # Python dependencies
├── .env                   # Configuration (copy from .env.example)
├── run.py                 # Application runner
├── init_db.py            # Database initializer
├── start.bat             # Windows startup script
├── start.sh              # Linux/Mac startup script
└── README.md             # Documentation
```
