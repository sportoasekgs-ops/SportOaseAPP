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

**Database**: SQLite (`sportoase.db`)

**Schema Design**:
- `users` table: Stores user credentials and roles (teacher/admin)
  - Password hashing using `werkzeug.security`
  - Email-based authentication
  - Role column with CHECK constraint (teacher/admin only)

- `bookings` table: Stores all booking records
  - Date and period (1-6) tracking
  - Student information stored as JSON in `students_json` column
  - Offer type classification (fest/frei)
  - Foreign key relationship to users table
  - Created timestamp for audit trail

**Data Model Rationale**: 
- SQLite chosen for simplicity and Replit compatibility
- JSON storage for student data provides flexibility for variable numbers of students per booking
- Row factory pattern enables dictionary-like access to query results

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
- Graceful degradation: prints notifications to console when SMTP not configured
- Purpose: Automated booking notifications to administrators and teachers

**Python Packages**:
- Flask: Web framework
- pytz: Timezone handling (Europe/Berlin)
- werkzeug: Password hashing utilities
- smtplib & email.mime: Email functionality (standard library)

**Configuration**:
- Period times, fixed offerings, and free modules defined in `config.py`
- Environment-based SMTP configuration for deployment flexibility
- Default admin credentials created during database initialization

## Recent Changes

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
