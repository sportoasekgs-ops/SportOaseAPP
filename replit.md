# SportOase Buchungssystem

## Overview

SportOase Buchungssystem is a web-based booking management system for a school sports facility. The application enables teachers to book time slots for students (1-5 per slot) and provides administrators with management capabilities for teachers and bookings. The system includes a weekly schedule with fixed and flexible offerings, capacity controls, and email notifications for new bookings.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture

**Template Engine**: Jinja2 (Flask templates)
- Base template pattern for consistent layout across all pages
- Simple HTML/CSS design with black-and-white color scheme
- Responsive layout suitable for desktop and tablet devices
- Key templates: login, dashboard (with weekly overview), booking form, admin panel

**Static Assets**:
- Minimal CSS in `/static/style.css` for clean, professional styling
- No JavaScript frameworks - vanilla JS for dynamic form interactions (e.g., student field generation)

### Backend Architecture

**Web Framework**: Flask (Python 3.11)
- Session-based authentication using Flask sessions
- Decorator-based route protection (`@login_required`, `@admin_required`)
- Timezone-aware datetime handling using `pytz` (Europe/Berlin)

**Application Structure**:
- `app.py`: Main application file containing all route handlers
- `config.py`: Configuration settings for class periods, fixed/free offerings, and module options
- `models.py`: Database interaction layer with SQLite
- `email_service.py`: SMTP-based email notification service
- `db_setup.py`: Database initialization script

**Key Features**:
- Role-based access control (teacher vs. admin)
- Booking validation: 60-minute advance booking requirement, 5-student maximum capacity per slot
- Weekly schedule display with fixed vs. flexible time slots with booking information (who booked, how many students)
- Dynamic module selection for flexible time slots
- Admin booking management: create, edit, and delete bookings with full validation
- Capacity-aware editing that prevents overbooking

### Data Storage

**Database**: PostgreSQL (Neon-backed via Replit)

**ORM**: Flask-SQLAlchemy 3.1.1

**Architecture**:
- `database.py`: Central SQLAlchemy instance shared across the application
- `models.py`: ORM model definitions (User, Booking, SlotName) and helper functions
- `db_setup.py`: Explicit database initialization and admin account creation

**Schema Design**:
- `users` table: Stores user credentials and roles (teacher/admin)
  - Password hashing using `werkzeug.security`
  - Username-based authentication (switched from email)
  - Role column for access control
  - Email field for notifications

- `bookings` table: Stores all booking records
  - Date and period (1-6) tracking
  - Student information stored as JSON in `students_json` column
  - Offer type classification (fest/frei)
  - Foreign key relationship to users table
  - Created timestamp for audit trail

- `slot_names` table: Stores customizable names for fixed slots
  - Weekday and period as unique key
  - Label field for custom slot names
  - Allows admins to rename fixed slots without changing config.py
  - Falls back to default names from FIXED_OFFERS if no custom name exists

- `blocked_slots` table: Stores temporarily blocked time slots for admin use
  - Date and period as unique key
  - Reason field for blocking purpose (e.g., "Beratung")
  - Foreign key to users table (which admin blocked it)
  - Prevents regular users from booking blocked periods
  - Admins can block/unblock slots via dashboard UI

**Data Model Rationale**: 
- PostgreSQL chosen for production deployment compatibility (Render)
- SQLAlchemy ORM provides type safety and easier migrations
- JSON storage for student data provides flexibility for variable numbers of students per booking
- Centralized database instance prevents initialization conflicts
- SlotName table enables dynamic slot renaming without code changes

### Authentication & Authorization

**Authentication Mechanism**: Session-based authentication
- Flask server-side sessions with secret key
- Hashed passwords (werkzeug's generate_password_hash/check_password_hash)
- Login credentials: email + password

**Authorization Levels**:
- Teachers: Can create bookings, view dashboard
- Admins: Full teacher permissions plus user management and booking overview

**Session Management**:
- User ID, email, and role stored in session
- Decorator functions enforce authentication and authorization requirements
- Logout clears session data

### External Dependencies

**SMTP Email Service**:
- Environment variables for configuration: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`, `ADMIN_EMAIL`
- Admin email: sportoase.kg@gmail.com (receives all booking notifications)
- Graceful degradation: prints notifications to console when SMTP not configured
- Purpose: Automated booking notifications to administrators and teachers

**Python Packages**:
- Flask 3.1.2: Web framework
- Flask-SQLAlchemy 3.1.1: ORM for PostgreSQL
- psycopg2-binary 2.9.11: PostgreSQL adapter
- gunicorn 23.0.0: Production WSGI server
- pytz 2025.2: Timezone handling (Europe/Berlin)
- werkzeug 3.1.3: Password hashing utilities
- email-validator 2.3.0: Email validation
- smtplib & email.mime: Email functionality (standard library)

**Configuration**:
- Period times, fixed offerings, and free modules defined in `config.py`
- Environment-based SMTP configuration for deployment flexibility
- Default admin credentials created during database initialization

### Deployment

**Platform**: Render (https://render.com)

**Database**: PostgreSQL on Render (free tier, 90-day expiration)

**Key Files**:
- `requirements.txt`: Python dependencies for deployment
- `DEPLOYMENT.md`: Complete deployment guide for Render
- `db_setup.py`: Database initialization script (MUST be run after first deploy)

**Environment Variables Required**:
- `DATABASE_URL`: PostgreSQL connection string (from Render)
- `SESSION_SECRET`: Random secret for Flask sessions
- `ADMIN_EMAIL`: sportoase.kg@gmail.com (for booking notifications)
- Optional SMTP settings for email notifications

**Important Notes**:
- Schema is NOT created automatically - run `python db_setup.py` after deployment
- Default admin account: username `sportoase`, password `mauro123`, email `sportoase.kg@gmail.com`
- Change admin password after first login!

## Recent Changes

- 2024-11-15: **Admin Slot Blocking for Consultation Meetings**
  - **Slot Blocking Feature**: Admins can now block time slots for consultation meetings (Beratungsgespräche)
    - Created `BlockedSlot` database model with date/period unique constraint
    - Foreign key to users table tracks which admin blocked each slot
    - Reason field stores blocking purpose (e.g., "Beratung")
    - Admin routes with CSRF protection for secure slot management
  - **Dashboard UI Enhancements**:
    - Added "Blockieren" buttons for admins on all unblocked slots
    - Added "Freigeben" buttons for admins on blocked slots
    - Blocked slots displayed in distinctive red styling (.period-blocked class)
    - Both weekly overview and daily view show blocking controls
  - **Booking Logic Updates**:
    - Booking route validates blocked status before displaying form (GET)
    - POST requests also validate and reject bookings for blocked slots
    - Flash messages inform users when attempting to book blocked slots
  - **Security**:
    - CSRF token validation on all admin block/unblock routes
    - Invalid tokens rejected with error message and redirect
    - Admin-only access enforced via @admin_required decorator

- 2024-11-14: **New Interactive Features & UX Improvements**
  - **Clickable Week Overview Slots**: Users can now click directly on slots in the week overview to access the booking form
    - Added `can_book` and `available` information to week overview data
    - Implemented visual affordance with hover effects and booking action indicators
    - Shows availability status and free slots for each period
    - CSS styling with gradient backgrounds and hover animations
  - **Admin Slot Name Management**: Admins can now customize the names of fixed slots
    - Created new `SlotName` database model for storing custom slot names
    - Added `/admin/manage_slots` route with management interface
    - Implemented modal-based editing UI with data attributes for security
    - Custom names override default FIXED_OFFERS from config.py
    - Protected against XSS with proper textContent usage
    - Fixed JavaScript security issue with apostrophes in slot names
  - **Database Schema Update**:
    - Added `slot_names` table with weekday/period unique constraint
    - Integrated custom slot names into `get_period_info()` function
    - Custom names propagate through dashboard, week overview, and booking forms
  - **UI/UX Enhancements**:
    - Added admin quick-links section with accent buttons
    - Improved CSS with clickable-slot and booking-action styles
    - Modal interface for slot renaming with live preview
    - Consistent color scheme using existing design variables

- 2024-11-14: **Major Migration: SQLite → PostgreSQL**
  - **Database Migration**: Migrated from SQLite to PostgreSQL for production deployment
    - Created `database.py` with centralized SQLAlchemy instance
    - Refactored `models.py` to use Flask-SQLAlchemy ORM instead of raw SQL
    - Converted all database queries from sqlite3 to SQLAlchemy
    - Removed automatic schema creation from app startup
    - Made schema creation explicit via `db_setup.py`
  - **Email Configuration Update**:
    - Changed admin email from `admin@school.de` to `sportoase.kg@gmail.com`
    - Updated `config.py` ADMIN_EMAIL default
    - Modified `db_setup.py` to create admin with correct email
    - Updated existing admin user in database
  - **Deployment Preparation**:
    - Created `requirements.txt` with all dependencies
    - Created comprehensive `DEPLOYMENT.md` with Render deployment guide
    - Configured PostgreSQL connection with environment variables
    - Added production-ready gunicorn configuration
  - **Architecture Improvements**:
    - Single SQLAlchemy instance shared across application
    - Clean separation of database initialization from web app
    - Production-safe schema management


- 2024-11-14: Enhanced admin panel and week overview features
  - **Admin Booking Management**: Added full CRUD operations for bookings (create, edit, delete)
    - Admins can now create bookings on behalf of any teacher
    - Admins can edit existing bookings with all validations
    - Added capacity checks to prevent overbooking in admin workflows
    - Implemented safe error handling for all user inputs
  - **Week Plan Overview Enhancements**: 
    - Added booking information to weekly overview showing who booked each slot
    - Display teacher names and student counts for each booking
    - Week overview now shows total students per period
  - **Data Safety Improvements**:
    - Guarded all JSON parsing against invalid/missing data
    - Added proper exception handling for form input validation
    - Fixed sqlite3.Row object handling throughout the application
  - Created `admin_edit_booking.html` template for admin booking form
  - Added database functions: `get_booking_by_id`, `update_booking`, `get_bookings_for_week`

- 2024-11-14: Initial implementation of complete SportOase booking system
  - Created all core files (app.py, config.py, models.py, db_setup.py, email_service.py)
  - Implemented authentication system with role-based access control
  - Built dashboard with weekly schedule overview and booking availability display
  - Created booking form with capacity validation and 60-minute advance requirement
  - Developed admin panel for teacher management and booking overview
  - Designed black-and-white responsive UI with all templates
  - Configured workflow to run Flask app on port 5000
  - Initialized database with default admin account (admin@sportoase.de / admin123)
