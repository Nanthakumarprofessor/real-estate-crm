# Real Estate CRM

A production-minded Customer Relationship Management system built for a real estate sales team. The application manages the complete sales workflow from initial lead capture through property viewing, unit selection, and confirmed booking — with role-based access for Admin and Sales employees, a live dashboard, and full property inventory management across a Project → Building → Unit hierarchy.

---

## Key Features

### Authentication
- JWT-based login and session management
- Session restored on page refresh via `/api/auth/me`
- Protected frontend routes redirect unauthenticated users to `/login`
- Token stored in `localStorage`; cleared on logout

### Role-Based Access Control
- Two roles: **Admin** and **Sales Employee**
- Backend enforces all permissions independently
- Frontend hides/disables actions the current role cannot perform — purely for UX
- Admin-only `/users` route protected by both frontend guard and backend authorization

### Lead Management
- Create, view, edit, and soft-delete leads
- Seven pipeline stages: New → Contacted → Site Visit → Interested → Negotiation → Booked → Lost
- Lead sources: Website, Referral, Advertisement, Walk-in, Social Media, Other
- Lead assignment: Admin can assign/reassign; Sales see only their own assigned leads
- Inline lead notes (append-only; role-aware deletion)
- Follow-ups with date/time, status (Pending / Completed / Cancelled), and overdue indicators
- Search by name, email, phone; filter by stage; backend-side pagination

### Property Management
Three-level hierarchy: **Project → Building → Unit**

- Admin: full CRUD on all levels
- Sales: read-only access to browse inventory
- Unit fields: unit number, type (1/2/3/4 BHK, Villa, Plot), floor, price, status (Available / Booked)
- Duplicate unit number within same building rejected with 409
- Buildings loaded lazily when a project is opened; units loaded lazily when a building is expanded

### Booking Management
- Create a booking by selecting: Lead → Project → Building → Available Unit
- Optional booking amount
- Booking statuses: Confirmed / Cancelled
- Admin can cancel confirmed bookings; unit reverts to Available
- Sales can only book their own assigned leads; cannot cancel
- **Double-booking prevention** — see Concurrency section below

### Dashboard
Role-scoped summary visible immediately after login:
- Total active leads with stage-by-stage pipeline breakdown
- Upcoming and overdue follow-up counts
- Property inventory: total / available / booked units
- Confirmed and cancelled booking counts
- Refresh button re-fetches data without a full page reload

### User Management *(Admin only)*
- List, create, edit, deactivate, and reactivate CRM users
- Role assignment (Admin / Sales)
- Last-admin protection: cannot deactivate or demote the final active Admin
- Search by name or email; filter by role or active status

### UI / UX
- Responsive: desktop tables, tablet layouts, mobile card stacks
- Loading skeletons for all major data fetches
- Empty states with context-aware CTAs
- Error states with retry buttons
- Toast notifications for every mutation
- Scrollable modals — all form fields and action buttons accessible on small screens
- Accessible labels on all interactive elements

---

## Technology Stack

### Backend
| Technology | Version |
|---|---|
| Python | 3.12 |
| FastAPI | latest |
| SQLAlchemy | 2.x |
| PostgreSQL | 14+ |
| Pydantic | v2 |
| Alembic | latest |
| passlib / bcrypt | latest |
| python-jose | latest |
| pytest | latest |
| uv | latest |

### Frontend
| Technology | Version |
|---|---|
| React | 18.3 |
| TypeScript | 5.5 |
| Vite | 5.3 |
| React Router | 6.24 |
| Axios | 1.7 |
| Bootstrap | 5.3 (CDN) |
| Bootstrap Icons | 1.11 (CDN) |

---

## Architecture

```
Browser (React + TypeScript)
        │
        │  Axios (JWT Bearer header)
        ▼
FastAPI REST API  (/api/...)
        │
        │  Python service layer
        ▼
SQLAlchemy 2.x ORM
        │
        ▼
PostgreSQL Database
```

**Backend authorization is always authoritative.** The frontend role checks only control which UI elements are shown; the backend independently validates every request regardless of what the frontend sends.

---

## Project Structure

```
task_project/
├── README.md
├── .gitignore
│
├── backend/
│   ├── pyproject.toml          # dependencies (uv)
│   ├── uv.lock
│   ├── alembic.ini
│   ├── main.py                 # uvicorn entry point
│   ├── .env.example            # environment template
│   │
│   ├── alembic/
│   │   └── versions/           # migration scripts
│   │
│   ├── src/
│   │   ├── main.py             # FastAPI app factory
│   │   ├── settings.py         # pydantic-settings config
│   │   │
│   │   ├── core/
│   │   │   └── security.py     # JWT, hashing, auth dependencies
│   │   │
│   │   ├── router/
│   │   │   ├── router.py       # API router registration
│   │   │   ├── auth_router.py
│   │   │   ├── user_router.py
│   │   │   ├── lead_router.py
│   │   │   ├── follow_up_router.py
│   │   │   ├── project_router.py
│   │   │   ├── building_router.py
│   │   │   ├── unit_router.py
│   │   │   ├── booking_router.py
│   │   │   └── dashboard_router.py
│   │   │
│   │   ├── service/
│   │   │   ├── auth_service.py
│   │   │   ├── user_service.py
│   │   │   ├── lead_service.py
│   │   │   ├── lead_note_service.py
│   │   │   ├── follow_up_service.py
│   │   │   ├── property_service.py
│   │   │   ├── booking_service.py
│   │   │   └── dashboard_service.py
│   │   │
│   │   ├── repository/
│   │   │   ├── database.py     # SQLAlchemy engine & session
│   │   │   └── models/         # ORM models
│   │   │
│   │   ├── models/             # Pydantic request/response DTOs
│   │   │
│   │   ├── utils/
│   │   │   ├── enums.py        # shared domain enums
│   │   │   ├── pagination.py
│   │   │   ├── logger.py
│   │   │   └── exceptions/
│   │   │
│   │   └── migration/
│   │       └── seed.py         # demo data seeder
│   │
│   └── tests/
│       ├── conftest.py
│       ├── test_health.py
│       ├── test_database.py
│       ├── test_auth.py
│       ├── test_users.py
│       ├── test_leads.py
│       ├── test_properties.py
│       ├── test_bookings.py
│       └── test_dashboard.py
│
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── index.html
    ├── .env.example
    │
    └── src/
        ├── main.tsx            # app entry point
        ├── App.tsx             # route tree
        ├── crm.css             # application shell styles
        │
        ├── api/                # Axios API modules
        ├── context/            # AuthContext
        ├── routes/             # ProtectedRoute, RoleProtectedRoute
        ├── hooks/              # useToast, useApiError
        ├── utils/              # token helpers
        │
        ├── pages/
        │   ├── LoginPage.tsx
        │   ├── DashboardPage.tsx
        │   ├── LeadsPage.tsx
        │   ├── PropertiesPage.tsx
        │   ├── BookingsPage.tsx
        │   └── UsersPage.tsx
        │
        └── components/
            ├── layout/         # AppLayout, Sidebar, Topbar
            ├── common/         # PageHeader, EmptyState, ConfirmModal, ToastContainer
            ├── dashboard/      # StatCard, LeadPipeline, PropertySummary, etc.
            ├── leads/          # LeadTable, LeadForm, LeadDetails, LeadNotes, LeadFollowUps
            ├── properties/     # ProjectForm, ProjectDetails, BuildingForm, UnitTable, UnitForm
            ├── bookings/       # BookingTable, BookingForm, BookingDetails, BookingFilters
            └── users/          # UserTable, UserForm, UserDetails, UserFilters
```

---

## Setup Instructions

### Prerequisites
- Python 3.12
- PostgreSQL 14+
- Node.js 18+ and npm
- [uv](https://docs.astral.sh/uv/) (Python package manager)

---

### Backend Setup

**1. Install uv** (if not already installed)
```bash
pip install uv
# or on macOS/Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**2. Create and activate the virtual environment**
```bash
cd backend
uv sync
```

**3. Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your PostgreSQL credentials and a strong JWT secret
```

**4. Create the PostgreSQL database**
```sql
CREATE DATABASE real_estate_crm;
```

**5. Run database migrations**
```bash
uv run alembic upgrade head
```

**6. (Optional) Seed demo data**
```bash
uv run python -m src.migration.seed
```

**7. Start the backend server**
```bash
uv run python main.py
```

The API will be available at `http://localhost:8000`
Swagger UI: `http://localhost:8000/docs`

---

### Frontend Setup

**1. Install dependencies**
```bash
cd frontend
npm install
```

**2. Configure environment** *(optional for local dev — Vite proxy handles it)*
```bash
cp .env.example .env
# VITE_API_BASE_URL is already set correctly for local development
```

**3. Start the development server**
```bash
npm run dev
```

The app will be available at `http://localhost:5173`

**4. Production build**
```bash
npm run build
```

---

### Running Both Services

Open two terminals:

```bash
# Terminal 1 — Backend
cd backend
uv run python main.py

# Terminal 2 — Frontend
cd frontend
npm run dev
```

---

## Environment Variables

### Backend (`backend/.env`)

```env
# PostgreSQL connection — psycopg3 driver
# Format: postgresql+psycopg://<user>:<password>@<host>:<port>/<dbname>
DATABASE_URL=postgresql+psycopg://postgres:password@localhost:5432/real_estate_crm

# JWT — generate a strong secret:
# python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET_KEY=change-this-to-a-long-random-secret
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60

# Application
APP_ENV=development
APP_DEBUG=true

# CORS — comma-separated allowed origins
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

### Frontend (`frontend/.env`)

```env
# API base URL — only needed for production builds.
# In development the Vite proxy (/api → localhost:8000) handles this.
VITE_API_BASE_URL=http://localhost:8000/api
```

---

## Demo Credentials

After running the seed script:

| Role  | Email                | Password   |
|-------|----------------------|------------|
| Admin | admin@example.com    | Admin@123  |
| Sales | sales@example.com    | Sales@123  |

---

## Database Schema

### Tables

| Table | Description |
|---|---|
| `users` | CRM users with role (ADMIN / SALES) and active status |
| `leads` | Potential customers with pipeline stage and source tracking |
| `lead_notes` | Append-only notes attached to a lead |
| `follow_ups` | Scheduled follow-up actions for a lead |
| `projects` | Real estate development projects |
| `buildings` | Buildings within a project |
| `units` | Individual property units within a building |
| `bookings` | Confirmed or cancelled unit bookings linked to a lead |

### Key Relationships

```
User ──(assigned_to)──► Lead ──► LeadNote
                            └──► FollowUp
                            └──► Booking ──► Unit ──► Building ──► Project
User ──(booked_by)────► Booking
```

### Important Constraints

| Constraint | Detail |
|---|---|
| Unique user email | `users.email` is globally unique |
| Unique unit number | `UNIQUE(building_id, unit_number)` — same number allowed in different buildings |
| One confirmed booking per unit | Partial unique index: `uix_unit_confirmed_booking ON bookings(unit_id) WHERE status = 'CONFIRMED'` |
| Lead cascade on delete | Notes and follow-ups cascade; bookings are restricted |
| Building restricted delete | Cannot delete a building that has units |
| Project restricted delete | Cannot delete a project that has buildings |
| Unit restricted delete | Cannot delete a unit that has booking records |

---

## API Overview

Base URL: `http://localhost:8000/api`
Interactive docs: `http://localhost:8000/docs`

### Authentication
```
POST   /api/auth/login          — obtain JWT token
GET    /api/auth/me             — get current user
```

### Users *(Admin only)*
```
GET    /api/users               — list users (search, role, active filters)
POST   /api/users               — create user
GET    /api/users/{id}          — get user
PUT    /api/users/{id}          — update user
PATCH  /api/users/{id}/deactivate — deactivate user
```

### Leads
```
POST   /api/leads               — create lead
GET    /api/leads               — list leads (search, stage, pagination)
GET    /api/leads/{id}          — get lead
PUT    /api/leads/{id}          — update lead
DELETE /api/leads/{id}          — soft-delete lead (Admin only)

POST   /api/leads/{id}/notes         — add note
GET    /api/leads/{id}/notes         — list notes
DELETE /api/leads/{id}/notes/{note_id} — delete note

POST   /api/leads/{id}/follow-ups    — create follow-up
GET    /api/leads/{id}/follow-ups    — list follow-ups for lead
GET    /api/follow-ups               — list all visible follow-ups
PUT    /api/follow-ups/{id}          — update follow-up
```

### Properties

**Projects**
```
POST   /api/projects                              — create
GET    /api/projects                              — list (search, pagination)
GET    /api/projects/{id}                         — get
PUT    /api/projects/{id}                         — update (Admin only)
DELETE /api/projects/{id}                         — delete (Admin only)
```

**Buildings**
```
POST   /api/projects/{project_id}/buildings       — create
GET    /api/projects/{project_id}/buildings       — list
GET    /api/buildings/{id}                        — get
PUT    /api/buildings/{id}                        — update (Admin only)
DELETE /api/buildings/{id}                        — delete (Admin only)
```

**Units**
```
POST   /api/buildings/{building_id}/units         — create
GET    /api/buildings/{building_id}/units         — list (status/type filters, pagination)
GET    /api/units/{id}                            — get
PUT    /api/units/{id}                            — update (Admin only)
DELETE /api/units/{id}                            — delete (Admin only)
```

### Bookings
```
POST   /api/bookings                — create booking
GET    /api/bookings                — list bookings (status filter, pagination)
GET    /api/bookings/{id}           — get booking
PATCH  /api/bookings/{id}/cancel    — cancel booking (Admin only)
```

### Dashboard
```
GET    /api/dashboard/summary       — role-scoped CRM summary
```

---

## Role / Permission Matrix

| Feature | Admin | Sales |
|---|---|---|
| Dashboard | All metrics | Own metrics only |
| View Leads | All leads | Assigned leads only |
| Create Lead | ✅ | ✅ (auto-assigned to self) |
| Edit Lead | Any | Own assigned only |
| Assign / Reassign Lead | ✅ | ❌ |
| Delete Lead (soft) | ✅ | ❌ |
| Lead Notes | Any lead | Own assigned only |
| Delete Note | Any note | Own notes only |
| Follow-ups | Any lead | Own assigned only |
| View Projects / Buildings / Units | ✅ | ✅ (read-only) |
| Create / Edit / Delete Properties | ✅ | ❌ |
| View Bookings | All | Own bookings only |
| Create Booking | Any active lead | Own assigned leads only |
| Cancel Booking | ✅ | ❌ |
| User Management | ✅ | ❌ (route blocked) |

*Backend enforces all permissions. Frontend restrictions are for navigation and UX only.*

---

## Booking Concurrency & Consistency

Booking creation uses a **database transaction with row-level locking** to prevent two users from booking the same unit simultaneously:

```
BEGIN TRANSACTION
  SELECT unit FROM units WHERE id = :unit_id FOR UPDATE   ← exclusive row lock
  Verify unit.status == AVAILABLE
  INSERT booking (status = CONFIRMED)
  UPDATE unit.status = BOOKED
  UPDATE lead.stage  = BOOKED
COMMIT
```

Two layers of defence against double-booking:

1. **`SELECT FOR UPDATE`** — the unit row is locked for the transaction duration. Concurrent transactions block until the first commits.
2. **Partial unique index** — `uix_unit_confirmed_booking ON bookings(unit_id) WHERE status = 'CONFIRMED'` — a database-level backstop that raises `IntegrityError` if the application lock somehow fails. Caught and returned as `409 Conflict`.

**Cancellation flow:**
```
SELECT booking FOR UPDATE
SELECT unit    FOR UPDATE
booking.status → CANCELLED
unit.status    → AVAILABLE
lead.stage     → unchanged (history preserved)
COMMIT
```

The booking record is never deleted. A cancelled unit can be booked again.

---

## Design Decisions

### 1. Layered Backend Architecture
`Router → Service → SQLAlchemy` — routers stay thin and only handle HTTP concerns. Business logic, validation, and authorization live in the service layer. This keeps each layer testable in isolation.

### 2. Backend-Authoritative RBAC
The frontend hides/disables controls the current role cannot use (better UX), but every backend endpoint independently validates the authenticated user's permissions. There is no security boundary that exists only in the frontend.

### 3. Transaction-Safe Booking with SELECT FOR UPDATE
Rather than checking availability at the application level and hoping no concurrent request sneaks in, the booking service locks the unit row for the duration of the transaction. The database partial unique index acts as a final safety net.

### 4. Lazy Property Hierarchy Loading
Buildings are fetched only when the user opens a project detail. Units are fetched only when a building is expanded. This avoids N+1 request patterns and keeps the initial page load fast regardless of how many properties exist.

### 5. Reusable Frontend Component System
Common patterns — `ConfirmModal`, `ToastContainer`, `EmptyState`, `PageHeader`, `LoadingSpinner` — are implemented once and reused across all pages. All data-fetching pages follow the same `loading / error / data` state pattern for consistency.

---

## Validation & Error Handling

### Backend
- Pydantic v2 validates all request bodies; invalid input returns `422 Unprocessable Entity`
- Custom `AppException` hierarchy maps business errors to appropriate HTTP status codes
- All errors return a consistent `{ "detail": "...", "error_code": "..." }` body
- Raw SQLAlchemy exceptions are never exposed; `IntegrityError` is caught and converted

| Status | Meaning |
|---|---|
| 400 | Business rule violation (e.g. last-admin protection) |
| 401 | Unauthenticated or token expired |
| 403 | Authenticated but insufficient permissions |
| 404 | Resource not found |
| 409 | Conflict (duplicate, dependency violation, booking concurrency) |
| 422 | Request validation failure |

### Frontend
- All API errors parsed by `parseApiError()` — raw backend messages never displayed directly
- Every form disables submission while saving and shows a spinner
- Destructive actions require confirmation via `ConfirmModal`
- Toast notifications confirm every successful mutation

---

## Testing

### Backend

```bash
cd backend
uv run pytest -q
```

**Result: 309 passed, 0 failed, 0 errors**

Test coverage:
| File | Tests |
|---|---|
| `test_health.py` | Health endpoint |
| `test_database.py` | Database connectivity |
| `test_auth.py` | Authentication flows |
| `test_users.py` | User management (36 cases) |
| `test_leads.py` | Lead management (64 cases) |
| `test_properties.py` | Property management (68 cases) |
| `test_bookings.py` | Booking workflow incl. concurrency (41 cases) |
| `test_dashboard.py` | Dashboard aggregates (36 cases) |

### Frontend

```bash
cd frontend
npm run build
```

**Result: 0 TypeScript errors, 0 build warnings, 0 build errors**

---

## Screenshots

*Capture and add to `docs/screenshots/` after running the application locally.*

Recommended screenshots:

- [ ] `01_login.png` — Login page
- [ ] `02_dashboard_admin.png` — Admin dashboard with live metrics
- [ ] `03_dashboard_sales.png` — Sales dashboard (scoped metrics)
- [ ] `04_leads_list.png` — Leads page with table and filters
- [ ] `05_lead_details.png` — Lead detail drawer with notes and follow-ups
- [ ] `06_properties.png` — Properties page with project cards
- [ ] `07_project_details.png` — Project detail with expanded building and units
- [ ] `08_booking_form.png` — Booking creation form (Project → Building → Unit cascade)
- [ ] `09_bookings_list.png` — Bookings page with status badges
- [ ] `10_users.png` — Users management page (Admin only)
- [ ] `11_mobile_leads.png` — Mobile responsive view (leads cards)
- [ ] `12_mobile_sidebar.png` — Mobile sidebar/drawer

---

## Assignment Requirement Checklist

- [x] JWT Authentication and session management
- [x] Role-based access control (Admin / Sales)
- [x] Lead management with full CRUD
- [x] Lead pipeline stages (7 stages)
- [x] Lead source tracking
- [x] Lead assignment (Admin assigns; Sales own-only)
- [x] Lead notes (append-only, role-aware deletion)
- [x] Follow-up scheduling and status management
- [x] Project management
- [x] Building management
- [x] Unit management with type / price / status
- [x] Booking workflow (Lead → Unit → Booking)
- [x] Double-booking prevention (SELECT FOR UPDATE + unique index)
- [x] Booking cancellation with state rollback
- [x] Dashboard with role-scoped analytics
- [x] Responsive frontend (desktop / tablet / mobile)
- [x] Form validation (client-side + server-side)
- [x] Permission enforcement (backend-authoritative)
- [x] Graceful error handling (400/401/403/404/409/422)
- [x] PostgreSQL relational database
- [x] Alembic database migrations
- [x] Seed data for demo
- [x] REST API with Swagger documentation
- [x] Automated backend test suite (309 tests)
- [x] Professional README and documentation
