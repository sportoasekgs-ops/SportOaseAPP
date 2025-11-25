# SportOase Buchungssystem

## Overview

SportOase Buchungssystem is a web-based booking management system designed for school sports facilities. It enables teachers to efficiently book time slots for students (1-5 per slot) and provides administrators with comprehensive tools for managing teachers and bookings. The system features a dynamic weekly schedule, capacity controls, and real-time email notifications for new bookings, ensuring smooth operation and effective resource allocation.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend

The frontend uses Jinja2 templates (Flask) for rendering, ensuring a consistent layout with a base template. The design features a simple black-and-white color scheme, is responsive for desktop and tablet devices, and avoids heavy JavaScript frameworks by using vanilla JS for dynamic elements. Key templates include login, dashboard (with a weekly overview), booking forms, and an admin panel.

### Backend

Built with Flask (Python 3.11), the backend implements session-based authentication, role-based access control (`@login_required`, `@admin_required`), and timezone-aware datetime handling (Europe/Berlin). The application structure separates concerns into `app.py` (routes), `config.py` (settings), `models.py` (database interaction), `email_service.py` (SMTP notifications), and `db_setup.py` (initialization). It features booking validation (60-minute advance, 5-student max), past date detection, dynamic module selection, and full CRUD operations for admin booking management with capacity awareness.

### Data Storage

The system utilizes PostgreSQL (Neon-backed via Replit) with Flask-SQLAlchemy 3.1.1 for ORM. The schema includes `users` (credentials, roles, email), `bookings` (date, period, student data as JSON, offer type), `slot_names` (customizable names for fixed slots), and `blocked_slots` (admin-blocked time slots with reasons). Password hashing is handled by `werkzeug.security`.

### Authentication & Authorization

**Dual Authentication System**: The application supports both traditional password-based login and IServ SSO (Single Sign-On) via OAuth2/OpenID Connect.

- **Traditional Login**: Password-based authentication with hashed passwords (`werkzeug.security`).
- **IServ SSO**: OAuth2/OpenID Connect integration using Authlib library for seamless login through school IServ credentials.
  - Admin role: morelli.maurizio@kgs-pattensen.de
  - Teacher role: All other IServ users
  - Users are identified by email across both authentication methods
  - OAuth users are stored with `oauth_provider='iserv'` and unique `oauth_id`

**Session Management**: Session-based authentication storing user ID, email, and role in Flask sessions. SESSION_SECRET environment variable is enforced for security (no fallback allowed).

**Authorization**: Two roles are defined:
- **Teachers**: Create bookings, view dashboard
- **Admins**: Full teacher permissions plus user/booking management

**Allowed Groups/Roles for Teacher Access**:
- Lehrer
- Mitarbeitende
- Mitarbeiter
- Pädagogische Mitarbeiter
- Sozialpädagogen
- Beratung
- Fairplaycoaches
- Any group containing: "lehrer", "mitarbeiter", "pädagog", "sozial"

### UI/UX Decisions

The UI features a modern card-based booking form design with improved visual hierarchy, professional gradient backgrounds, and shadow effects. Past dates are visually greyed out, and blocked slots are distinctly marked. Admin panels include quick-links and modal-based editing for slot management. A real-time notification system with a bell icon, unread badge, dropdown menu, and sound alerts for new bookings enhances the admin experience.

### Technical Implementations & Feature Specifications

- **Past Date Protection**: Comprehensive backend validation and frontend visual cues prevent booking of past time slots.
- **Modernized Booking Form**: Redesigned booking interface with a card-based layout, icons, and improved responsiveness.
- **Admin Slot Blocking**: Admins can block/unblock time slots for special purposes, visually indicated on the dashboard.
- **Interactive Week Overview**: Clickable slots in the weekly overview link directly to booking forms, showing availability.
- **Admin Slot Name Management**: Admins can customize fixed slot names via a management interface, overriding `config.py` defaults.
- **Real-Time Notification System**: Integrated with Gmail API for email notifications and Server-Sent Events (SSE) for live updates to the admin dashboard, including unread counts and sound alerts.
- **CSRF Protection**: All POST requests are protected with CSRF tokens.
- **IServ SSO Integration**: OAuth2/OpenID Connect implementation using Authlib for seamless login through school IServ server. Supports automatic role assignment based on email domain. See `ISERV_INTEGRATION_SETUP.md` for configuration details.

## External Dependencies

- **SMTP Email Service**: Configured via environment variables (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`, `ADMIN_EMAIL`) for automated booking notifications. Admin email: `sportoase.kg@gmail.com`.
- **Python Packages**:
    - `Flask` (Web framework)
    - `Flask-SQLAlchemy` (ORM)
    - `psycopg2-binary` (PostgreSQL adapter)
    - `gunicorn` (Production WSGI server)
    - `pytz` (Timezone handling)
    - `werkzeug` (Password hashing)
    - `email-validator` (Email validation)
    - `Authlib` (OAuth2/OpenID Connect for IServ SSO)
    - `smtplib`, `email.mime` (Standard library for email)
- **Database**: PostgreSQL (Neon-backed on Replit, deployed to Render). Schema includes OAuth fields (`oauth_provider`, `oauth_id`) for SSO support.
- **Gmail API**: Used for enhanced email notifications through Replit's Gmail connector.
- **IServ OAuth**: Requires configuration in IServ admin panel (`Verwaltung → System → Single-Sign-On`). Environment variables: `ISERV_BASE_URL`, `ISERV_CLIENT_ID`, `ISERV_CLIENT_SECRET`, `SESSION_SECRET`.