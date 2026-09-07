# Real Estate CRM — Software Design Specification (v2)

> **Status:** Reviewed and approved. Ready for implementation.
> **Version:** 2.0 — incorporates all changes from the architecture and requirements review.

---

## 1. Project Overview

Build a small, production-minded **Real Estate CRM** for a real-estate sales team.

The system will allow sales employees to:

* Manage potential customers (Leads)
* Track lead progress through different sales stages
* Assign leads to sales employees
* Add notes and follow-up dates
* Manage real-estate Projects, Buildings, and Units
* View unit availability
* Create bookings by connecting a Lead to a Property Unit
* Prevent duplicate bookings of the same unit
* View useful sales and booking metrics through a Dashboard

The application should be implemented as a focused MVP suitable for a **6–8 hour coding assignment**.

The priority is:

1. Correct business logic
2. Booking consistency and duplicate-booking prevention
3. Authentication and role-based permissions
4. Clean backend architecture
5. Professional and responsive UI
6. Good validation and error handling
7. Clear README and setup instructions

Do **not** over-engineer the solution with microservices, Kubernetes, Kafka, Redis, Terraform, or other infrastructure that is unnecessary for this assignment.

---

## 2. Recommended Technology Stack

### Backend

* Python 3.11+
* FastAPI
* SQLAlchemy 2.x
* PostgreSQL
* Pydantic v2
* JWT authentication
* Passlib/bcrypt for password hashing
* Alembic for database migrations
* Pytest for testing
* FastAPI OpenAPI/Swagger documentation

### Frontend

* React
* Vite
* React Router
* Axios
* Bootstrap or Tailwind CSS

The frontend should be responsive and professional.

### Development Tools

* Git
* GitHub
* VS Code / Kiro
* Postman or Swagger UI

---

## 3. User Roles

The application has two roles.

### 3.1 Admin

Admin users can:

* Login
* View dashboard (system-wide metrics)
* View all leads, including unassigned leads
* Create / edit / delete (soft) leads
* Assign or reassign leads to sales employees
* View all sales employees
* Create / manage projects
* Create / manage buildings
* Create / manage units
* View all bookings
* Create bookings for any valid lead
* Cancel bookings
* Manage users (create, edit, deactivate)
* View system-wide metrics

### 3.2 Sales Employee

Sales employees can:

* Login
* View dashboard restricted to their own assigned leads, follow-ups, and bookings
* View only leads assigned to them
* Create leads (unassigned leads they create must be reassignable by Admin)
* Edit their assigned leads
* Update lead stages
* Add notes to their assigned leads
* Delete their own notes
* Manage follow-ups for their assigned leads
* View available properties/units (read-only)
* Create bookings **only for leads assigned to them**
* View their own bookings

Sales employees **cannot**:

* View or manage unassigned leads they did not create
* Access another employee's leads
* Create a booking for a lead assigned to another employee
* Cancel bookings
* Manage users
* Create, edit, or delete projects, buildings, or units
* View other employees' notes or follow-ups

---

## 4. Authentication

Authentication must use JWT.

### Login

**Endpoint:** `POST /api/auth/login`

**Request:**

```json
{
  "email": "admin@example.com",
  "password": "Admin@123"
}
```

**Response:**

```json
{
  "access_token": "<jwt-token>",
  "token_type": "bearer"
}
```

The JWT must contain enough information to identify the authenticated user and their role.

Protected endpoints must require:

```
Authorization: Bearer <token>
```

The token expiry is controlled by `ACCESS_TOKEN_EXPIRE_MINUTES` in the environment configuration. When a token expires, the frontend must redirect to the login page.

### Current User

`GET /api/auth/me`

Returns the currently authenticated user.

```json
{
  "id": 1,
  "name": "Admin User",
  "email": "admin@example.com",
  "role": "ADMIN",
  "is_active": true
}
```

---

## 5. Lead Management

A Lead represents a potential customer interested in purchasing a property.

### Lead Stages

```text
NEW
CONTACTED
SITE_VISIT
INTERESTED
NEGOTIATION
BOOKED
LOST
```

Lead stage must use an enum, not arbitrary strings.

### Example Business Flow

```
Customer Rahul contacts the company
  → Lead created: stage = NEW

Sales employee calls Rahul
  → stage = CONTACTED

Rahul agrees to visit the property
  → stage = SITE_VISIT

Rahul likes Unit A-101
  → stage = INTERESTED

Price negotiation starts
  → stage = NEGOTIATION

Rahul agrees to purchase A-101
  → Sales employee creates booking
  → stage = BOOKED (set atomically with booking creation)
```

---

## 6. Lead Database Model

Table: `leads`

| Field       | Type         | Nullable | Description                         |
| ----------- | ------------ | -------- | ----------------------------------- |
| id          | Integer (PK) | No       | Primary key                         |
| name        | String       | No       | Customer name                       |
| email       | String       | Yes      | Customer email                      |
| phone       | String       | Yes      | Customer phone                      |
| source      | Enum         | Yes      | Lead source (see enum below)        |
| stage       | Enum         | No       | Current lead stage                  |
| assigned_to | FK → users   | **Yes**  | Assigned sales employee (nullable)  |
| is_active   | Boolean      | No       | Soft-delete flag, default = true    |
| created_at  | DateTime     | No       | Creation timestamp                  |
| updated_at  | DateTime     | No       | Last update timestamp (auto-update) |

### Lead Source Enum

```text
WEBSITE
REFERRAL
ADVERTISEMENT
WALK_IN
SOCIAL_MEDIA
OTHER
```

### Unassigned Lead Rules

* `assigned_to` is nullable. A lead may exist without an assigned employee.
* **Admin** can view, edit, and assign all leads, including unassigned ones.
* **Sales Employee** can only view leads where `assigned_to = their own user ID`. They cannot access unassigned leads unless specifically assigned to them.
* Admin can assign or reassign any lead at any time.

### Indexes

```sql
CREATE INDEX idx_leads_assigned_to ON leads(assigned_to);
CREATE INDEX idx_leads_stage ON leads(stage);
CREATE INDEX idx_leads_is_active ON leads(is_active);
```

---

## 7. Lead APIs

### Create Lead

`POST /api/leads`

```json
{
  "name": "Rahul Kumar",
  "email": "rahul@example.com",
  "phone": "9876543210",
  "source": "WEBSITE",
  "stage": "NEW",
  "assigned_to": 2
}
```

### List Leads

`GET /api/leads`

Supports pagination, search, stage filtering, and assigned-employee filtering.

```text
GET /api/leads?page=1&size=10
GET /api/leads?search=Rahul
GET /api/leads?stage=NEGOTIATION
GET /api/leads?assigned_to=2
```

**Response format** (all list endpoints use this structure):

```json
{
  "items": [],
  "total": 120,
  "page": 1,
  "size": 10
}
```

Admin receives all leads. Sales employee receives only their assigned leads.

### Get Lead

`GET /api/leads/{id}`

### Update Lead

`PUT /api/leads/{id}`

Sales employee may only update leads assigned to them.

### Delete Lead

`DELETE /api/leads/{id}`

Soft deletion only: sets `is_active = false`. Admin only.
Physical deletion is not performed.

---

## 8. Lead Notes

Sales employees can add notes to their assigned leads.

Notes are **append-only for the MVP**. Notes cannot be edited after creation.

### Database Model

Table: `lead_notes`

| Field      | Type         | Nullable | Description             |
| ---------- | ------------ | -------- | ----------------------- |
| id         | Integer (PK) | No       | Primary key             |
| lead_id    | FK → leads   | No       | Associated lead         |
| user_id    | FK → users   | No       | Author (user who added) |
| note       | Text         | No       | Note content            |
| created_at | DateTime     | No       | Creation timestamp      |

Notes do not have `updated_at` because they are immutable.

### Note Deletion Rules

* **Sales Employee** can delete only their own notes (`note.user_id == current_user.id`).
* **Admin** can delete any note.
* Sales Employee **cannot** delete another employee's note.

### APIs

Create note:

`POST /api/leads/{lead_id}/notes`

List notes:

`GET /api/leads/{lead_id}/notes`

Delete note:

`DELETE /api/leads/{lead_id}/notes/{note_id}`

---

## 9. Follow-Ups

Sales employees track upcoming customer follow-ups.

### Database Model

Table: `follow_ups`

| Field        | Type         | Nullable | Description                         |
| ------------ | ------------ | -------- | ----------------------------------- |
| id           | Integer (PK) | No       | Primary key                         |
| lead_id      | FK → leads   | No       | Associated lead                     |
| assigned_to  | FK → users   | No       | Responsible employee                |
| follow_up_at | DateTime     | No       | Scheduled follow-up datetime        |
| notes        | Text         | Yes      | Optional notes                      |
| status       | Enum         | No       | PENDING / COMPLETED / CANCELLED     |
| created_at   | DateTime     | No       | Creation timestamp                  |
| updated_at   | DateTime     | No       | Last update timestamp (auto-update) |

Follow-up status enum:

```text
PENDING
COMPLETED
CANCELLED
```

### Follow-Up Validation Rules

* `follow_up_at` **must not be in the past** when creating a new follow-up.
* Sales employees can only create and manage follow-ups for leads assigned to them.
* Admin can manage all follow-ups.

### Indexes

```sql
CREATE INDEX idx_followups_assignee_status
ON follow_ups(assigned_to, status, follow_up_at);
```

### APIs

Create follow-up:

`POST /api/leads/{lead_id}/follow-ups`

List follow-ups for a lead:

`GET /api/leads/{lead_id}/follow-ups`

Update follow-up:

`PUT /api/follow-ups/{id}`

List upcoming / filtered follow-ups:

`GET /api/follow-ups?status=PENDING`

Supports pagination using the standard pagination response format.

---

## 10. Property Management

The property hierarchy is:

```
Project
   ↓
Building
   ↓
Unit
```

Example:

```
ABC Residency (Project)
    ├── Tower A (Building)
    │      ├── A-101 (Unit)
    │      ├── A-102 (Unit)
    └── Tower B (Building)
           ├── B-101 (Unit)
           └── B-102 (Unit)
```

---

## 11. Projects

Table: `projects`

| Field       | Type         | Nullable | Description                         |
| ----------- | ------------ | -------- | ----------------------------------- |
| id          | Integer (PK) | No       | Primary key                         |
| name        | String       | No       | Project name                        |
| location    | String       | Yes      | Project location                    |
| description | Text         | Yes      | Description                         |
| created_at  | DateTime     | No       | Creation timestamp                  |
| updated_at  | DateTime     | No       | Last update timestamp (auto-update) |

### Deletion Rule

A project **must not be physically deleted** if it has associated buildings.
Use `RESTRICT` at the database level.

### APIs (Admin only)

```text
POST   /api/projects
GET    /api/projects
GET    /api/projects/{id}
PUT    /api/projects/{id}
DELETE /api/projects/{id}
```

---

## 12. Buildings

Table: `buildings`

| Field        | Type           | Nullable | Description                         |
| ------------ | -------------- | -------- | ----------------------------------- |
| id           | Integer (PK)   | No       | Primary key                         |
| project_id   | FK → projects  | No       | Parent project                      |
| name         | String         | No       | Building name                       |
| total_floors | Integer        | Yes      | Number of floors                    |
| created_at   | DateTime       | No       | Creation timestamp                  |
| updated_at   | DateTime       | No       | Last update timestamp (auto-update) |

Relationship: `Project 1 ───── N Buildings`

### Deletion Rule

A building **must not be physically deleted** if it has associated units.
Use `RESTRICT` at the database level.

### APIs (Admin only)

```text
POST   /api/projects/{project_id}/buildings
GET    /api/projects/{project_id}/buildings
GET    /api/buildings/{id}
PUT    /api/buildings/{id}
DELETE /api/buildings/{id}
```

---

## 13. Units

Table: `units`

| Field       | Type           | Nullable | Description                         |
| ----------- | -------------- | -------- | ----------------------------------- |
| id          | Integer (PK)   | No       | Primary key                         |
| building_id | FK → buildings | No       | Parent building                     |
| unit_number | String         | No       | Unit identifier within building     |
| type        | Enum           | No       | Unit type (see enum below)          |
| floor       | Integer        | Yes      | Floor number                        |
| price       | Decimal        | Yes      | Listing price (≥ 0 if provided)     |
| status      | Enum           | No       | AVAILABLE / BOOKED                  |
| created_at  | DateTime       | No       | Creation timestamp                  |
| updated_at  | DateTime       | No       | Last update timestamp (auto-update) |

### Unit Type Enum

```text
1BHK
2BHK
3BHK
4BHK
VILLA
PLOT
```

### Unit Status Enum

```text
AVAILABLE
BOOKED
```

### Unique Constraint

A building must not contain duplicate unit numbers:

```sql
UNIQUE(building_id, unit_number)
```

### Deletion Rule

A unit **must not be physically deleted** if it has an active (CONFIRMED) booking.
Use `RESTRICT` at the database level.

### Indexes

```sql
CREATE INDEX idx_units_status ON units(status);
CREATE INDEX idx_units_building_status ON units(building_id, status);
```

---

## 14. Unit APIs

Create (Admin only):

`POST /api/buildings/{building_id}/units`

List:

`GET /api/buildings/{building_id}/units`

Supports filters:

```text
status=AVAILABLE
status=BOOKED
type=2BHK
```

Get:

`GET /api/units/{id}`

Update (Admin only):

`PUT /api/units/{id}`

Delete (Admin only):

`DELETE /api/units/{id}`

---

## 15. Booking Management

Booking is the **highest-priority business operation** in this application.

A booking connects:

```
Lead → Unit → User (booked_by)
```

Example:

```
Lead:      Rahul Kumar
Unit:      Tower A / A-101
Booked By: Sales Employee
```

---

## 16. Booking Database Model

Table: `bookings`

| Field        | Type         | Nullable | Description                                          |
| ------------ | ------------ | -------- | ---------------------------------------------------- |
| id           | Integer (PK) | No       | Primary key                                          |
| lead_id      | FK → leads   | No       | Associated lead                                      |
| unit_id      | FK → units   | No       | Booked unit                                          |
| booked_by    | FK → users   | No       | User who created the booking                         |
| booking_date | DateTime     | No       | **Server-generated. Defaults to NOW(). Not client-settable.** |
| amount       | Decimal      | **Yes**  | Optional booking amount. If provided, must be ≥ 0.  |
| status       | Enum         | No       | CONFIRMED / CANCELLED                                |
| created_at   | DateTime     | No       | Creation timestamp                                   |
| updated_at   | DateTime     | No       | Last update timestamp (auto-update)                  |

### booking_date Rule

`booking_date` is always set by the server at the time of booking creation (`DEFAULT NOW()`).
It is **never accepted from the client request payload**.

### amount Rule

`amount` is optional (nullable). If provided, it must be greater than or equal to zero. A negative amount must be rejected with HTTP 422.

### Booking Status Enum

```text
CONFIRMED
CANCELLED
```

### Indexes

```sql
CREATE INDEX idx_bookings_lead_id ON bookings(lead_id);
CREATE INDEX idx_bookings_booked_by ON bookings(booked_by);
CREATE INDEX idx_bookings_status ON bookings(status);
```

---

## 17. Critical Business Rule — No Duplicate Bookings

The same property unit must never have more than one CONFIRMED booking at any time.

Example:

```
Customer A → Unit A-101 → CONFIRMED BOOKING
```

If another employee attempts:

```
Customer B → Unit A-101 → booking attempt
```

The system must reject the second request with:

**HTTP `409 Conflict`**

```json
{
  "detail": "Unit A-101 is already booked"
}
```

This rule must be enforced at **both** the application level (row-level locking) **and** the database level (partial unique index).

### Mandatory Database Constraint

The following partial unique index is **required** and must be included in the Alembic migration:

```sql
CREATE UNIQUE INDEX uix_unit_confirmed_booking
ON bookings (unit_id)
WHERE status = 'CONFIRMED';
```

This constraint ensures that even if application logic has a bug, PostgreSQL will never allow two CONFIRMED bookings for the same unit. An `IntegrityError` from this constraint must be caught by the application and returned as HTTP 409.

---

## 18. Concurrency-Safe Booking

A simple availability check is **not sufficient**:

```python
# WRONG — race condition possible
if unit.status == "AVAILABLE":
    create_booking()
```

Two requests can check simultaneously, both see AVAILABLE, and both proceed to create a booking.

### Required Booking Transaction Flow

```
1. BEGIN TRANSACTION

2. SELECT * FROM units
   WHERE id = :unit_id
   FOR UPDATE
   ↓
   (acquires exclusive row-level lock on the unit row)
   (concurrent requests block here until this transaction completes)

3. Re-read unit.status inside the lock
   → If status != 'AVAILABLE':
       ROLLBACK
       → Return HTTP 409 Conflict: "Unit A-101 is already booked"

4. INSERT INTO bookings
   (lead_id, unit_id, booked_by, amount, status='CONFIRMED', booking_date=NOW())

5. UPDATE units
   SET status = 'BOOKED', updated_at = NOW()
   WHERE id = :unit_id

6. UPDATE leads
   SET stage = 'BOOKED', updated_at = NOW()
   WHERE id = :lead_id

7. COMMIT
```

After COMMIT, any blocked concurrent transaction acquires the lock, reads `status = BOOKED`, and returns HTTP 409.

### SQLAlchemy Implementation Note

Use `with_for_update()` on the unit query:

```python
stmt = select(Unit).where(Unit.id == unit_id).with_for_update()
unit = session.execute(stmt).scalar_one_or_none()
```

---

## 19. Booking Permissions

| Action | Admin | Sales Employee |
|--------|-------|----------------|
| Create booking (any valid lead) | ✅ | ❌ |
| Create booking (own assigned lead) | ✅ | ✅ |
| Create booking (another employee's lead) | ✅ | ❌ → HTTP 403 |
| Cancel booking | ✅ | ❌ → HTTP 403 |
| View all bookings | ✅ | ❌ (own only) |
| View own bookings | ✅ | ✅ |

**Rule:** A Sales Employee may only create a booking if `lead.assigned_to == current_user.id`.
Attempting to book a lead assigned to another employee returns HTTP 403 Forbidden.

---

## 20. Create Booking API

`POST /api/bookings`

**Request:**

```json
{
  "lead_id": 1,
  "unit_id": 5,
  "amount": 250000
}
```

`booking_date` must **not** be included in the request. It is set server-side.

**Backend steps:**

1. Authenticate user (require valid JWT).
2. Validate lead exists and is active.
3. Validate unit exists.
4. Enforce booking permission (admin: any lead; sales: own assigned lead only).
5. Begin database transaction.
6. Lock the unit row using `SELECT FOR UPDATE`.
7. Re-check unit status — if not AVAILABLE, return HTTP 409.
8. Insert booking record with `status = CONFIRMED` and `booking_date = NOW()`.
9. Update `units.status = BOOKED`.
10. Update `leads.stage = BOOKED`.
11. Commit transaction.

**Success response — HTTP 201 Created:**

```json
{
  "id": 10,
  "lead_id": 1,
  "unit_id": 5,
  "booked_by": 2,
  "booking_date": "2026-09-06T10:30:00Z",
  "amount": 250000,
  "status": "CONFIRMED"
}
```

**Already booked — HTTP 409 Conflict:**

```json
{
  "detail": "Unit A-101 is already booked"
}
```

---

## 21. Booking APIs

Create:

`POST /api/bookings`

List:

`GET /api/bookings`

Admin receives all bookings. Sales employee receives only their own bookings.

Get:

`GET /api/bookings/{id}`

Cancel:

`PATCH /api/bookings/{id}/cancel`

Admin only.

---

## 22. Concurrency-Safe Booking Cancellation

Cancellation must also be performed within a database transaction with row-level locking.

### Required Cancellation Transaction Flow

```
1. BEGIN TRANSACTION

2. SELECT * FROM bookings
   WHERE id = :booking_id
   FOR UPDATE
   ↓
   (acquires exclusive lock on booking row)

3. Verify booking.status == 'CONFIRMED'
   → If not CONFIRMED:
       ROLLBACK
       → Return HTTP 409: "Booking is not in CONFIRMED state"

4. UPDATE bookings
   SET status = 'CANCELLED', updated_at = NOW()
   WHERE id = :booking_id

5. SELECT * FROM units
   WHERE id = :unit_id
   FOR UPDATE
   ↓
   (lock the unit row)

6. UPDATE units
   SET status = 'AVAILABLE', updated_at = NOW()
   WHERE id = :unit_id

7. COMMIT
```

This prevents a race condition where a concurrent booking attempt could read the unit as AVAILABLE before cancellation completes.

---

## 23. Booking Validation

Before creating a booking, validate:

* Lead must exist.
* Lead must be active (`is_active = true`).
* Unit must exist.
* Unit status must be AVAILABLE.
* User must have permission to book this lead.
* Amount, if provided, must be ≥ 0.
* A CONFIRMED booking must not already exist for the unit (enforced by lock + partial unique index).

**HTTP response codes:**

```
201 Created          → successful booking
400 Bad Request      → malformed request
401 Unauthorized     → no/invalid token
403 Forbidden        → insufficient permission
404 Not Found        → lead or unit not found
409 Conflict         → unit already booked
422 Unprocessable    → validation failure (e.g. negative amount)
500 Internal Error   → unexpected server error
```

---

## 24. Users Database Model

Table: `users`

| Field         | Type          | Nullable | Description                         |
| ------------- | ------------- | -------- | ----------------------------------- |
| id            | Integer (PK)  | No       | Primary key                         |
| name          | String        | No       | Full name                           |
| email         | String UNIQUE | No       | Login email                         |
| password_hash | String        | No       | Bcrypt hash — never store plaintext |
| role          | Enum          | No       | ADMIN / SALES                       |
| is_active     | Boolean       | No       | Active flag, default = true         |
| created_at    | DateTime      | No       | Creation timestamp                  |
| updated_at    | DateTime      | No       | **Last update timestamp (auto-update on every change)** |

### User Deactivation Behavior

When an Admin deactivates a user (`is_active = false`):

* The user **cannot log in**. The login endpoint must check `is_active` and return HTTP 401 if false.
* All existing leads, bookings, notes, and follow-ups created by or assigned to the user **remain intact**.
* Assigned leads are **not automatically reassigned**. Admin must manually reassign them.
* The user's data is preserved for historical and audit purposes.

### User Role Enum

```text
ADMIN
SALES
```

Passwords must never be stored as plain text.

---

## 25. User Management APIs

Admin only.

```text
GET    /api/users              → list all users
POST   /api/users              → create a new user
GET    /api/users/{id}         → get user by ID
PUT    /api/users/{id}         → update user details
PATCH  /api/users/{id}/deactivate → deactivate user (sets is_active = false)
```

Deactivated users cannot log in. Their data is preserved.

---

## 26. Database Relationships and Cardinality

```
USERS
  │
  ├──────────────< LEADS          (User 1 → N Leads, assigned_to nullable)
  │                  │
  │                  ├────────< LEAD_NOTES
  │                  │
  │                  └────────< FOLLOW_UPS
  │
  ├──────────────< LEAD_NOTES     (User 1 → N Notes, author)
  │
  ├──────────────< FOLLOW_UPS     (User 1 → N FollowUps, assigned_to)
  │
  └──────────────< BOOKINGS       (User 1 → N Bookings, booked_by)


PROJECTS
  │
  └──────────────< BUILDINGS
                       │
                       └──────────────< UNITS
                                             │
                                             └────── BOOKINGS
                                                     (Unit 1 → 0..1 CONFIRMED Booking)

LEADS
  │
  └──────────────< BOOKINGS
```

### ON DELETE Behavior

| Relationship | ON DELETE |
|---|---|
| `users → leads` (assigned_to) | **SET NULL** — lead remains, assigned_to becomes null |
| `users → lead_notes` (user_id) | **RESTRICT** — cannot delete user with notes |
| `users → follow_ups` (assigned_to) | **RESTRICT** — cannot delete user with follow-ups |
| `users → bookings` (booked_by) | **RESTRICT** — cannot delete user with bookings |
| `leads → lead_notes` | **CASCADE** — delete lead → delete its notes |
| `leads → follow_ups` | **CASCADE** — delete lead → delete its follow-ups |
| `leads → bookings` | **RESTRICT** — cannot delete lead with active booking |
| `projects → buildings` | **RESTRICT** — cannot delete project with buildings |
| `buildings → units` | **RESTRICT** — cannot delete building with units |
| `units → bookings` | **RESTRICT** — cannot delete unit with bookings |

Where soft deletion applies (leads, users), prefer setting `is_active = false` rather than physical deletion.

---

## 27. Dashboard

`GET /api/dashboard/summary`

### Role-Scoped Metrics (Strict)

**Admin** receives **system-wide** metrics:

```json
{
  "total_leads": 120,
  "new_leads": 30,
  "contacted_leads": 25,
  "site_visits": 20,
  "interested_leads": 15,
  "negotiation_leads": 10,
  "booked_leads": 15,
  "lost_leads": 5,
  "total_projects": 4,
  "total_units": 150,
  "available_units": 100,
  "booked_units": 50,
  "total_bookings": 50,
  "upcoming_followups": 8
}
```

**Sales Employee** receives metrics **restricted to their own** assigned leads, bookings, and follow-ups:

```json
{
  "my_total_leads": 20,
  "my_new_leads": 5,
  "my_contacted_leads": 6,
  "my_site_visits": 3,
  "my_interested_leads": 2,
  "my_negotiation_leads": 2,
  "my_booked_leads": 2,
  "my_lost_leads": 0,
  "my_total_bookings": 2,
  "total_units": 150,
  "available_units": 100,
  "my_upcoming_followups": 3
}
```

The scoping is **mandatory**, not optional. A Sales Employee must never see metrics from other employees' leads or bookings.

---

## 28. Frontend Pages

### Login

Route: `/login`

* Email field
* Password field
* Login button
* Validation messages
* Error message on failed login
* Redirects to `/dashboard` on success

### Dashboard

Route: `/dashboard`

Display metric cards:

```
Total Leads (scoped by role)
New Leads
Negotiations
Bookings
Available Units
Upcoming Follow-ups
```

Charts or visual summaries may be added where they add value but are not required for the MVP.

### Leads

Route: `/leads`

* Lead table with columns: Name, Email, Phone, Source, Stage, Assigned To, Created
* Search by name/email
* Filter by stage
* Filter by assigned employee (Admin only)
* Pagination
* Create lead button (opens form/modal)
* Click row → Lead Details

### Lead Details

Route: `/leads/:id`

Display:

* Customer information
* Current stage (with update control)
* Assigned employee
* Notes (list + add note form)
* Follow-ups (list + create follow-up form with date validation)
* Booking information if the lead has a CONFIRMED or CANCELLED booking

Allow:

* Stage update via dropdown
* Add note (append-only)
* Delete own note
* Create follow-up (date must not be in the past)
* Edit lead details

### Properties

Route: `/properties`

Display hierarchy:

```
Projects
  └── Buildings
        └── Units
```

Unit list shows:

* Unit Number
* Type
* Floor
* Price
* Status (AVAILABLE / BOOKED — visually distinct, e.g. green/red badge)

Admin controls for creating/editing projects, buildings, units.
Sales employees see the properties in read-only mode.

### Bookings

Route: `/bookings`

Display columns:

* Lead name
* Project / Building / Unit
* Amount
* Booking date
* Status (CONFIRMED / CANCELLED)
* Booked by

Admin sees all bookings. Sales employee sees only their own.

---

## 29. Booking UI

The booking form must present a **cascading selection**:

```
Step 1: Select Lead (must be assigned to current user for Sales)
Step 2: Select Project
Step 3: Select Building (filtered by selected project)
Step 4: Select Available Unit (only units with status=AVAILABLE in selected building)
Step 5: Enter Amount (optional)
Step 6: Submit
```

The unit selector must **only display units with status = AVAILABLE**.

### Frontend Conflict Handling

The frontend availability check is a UX aid only. The backend is the authority.

If the API returns HTTP 409 after submission (unit booked between page load and submission), the frontend must display:

```
"This unit was just booked by someone else. Please select another unit."
```

The form should remain open so the user can select a different unit.

---

## 30. Frontend Architecture

Recommended structure:

```
frontend/
├── src/
│   ├── components/
│   │   ├── common/
│   │   ├── forms/
│   │   ├── tables/
│   │   └── layout/
│   │
│   ├── pages/
│   │   ├── Login.jsx
│   │   ├── Dashboard.jsx
│   │   ├── Leads.jsx
│   │   ├── LeadDetails.jsx
│   │   ├── Properties.jsx
│   │   └── Bookings.jsx
│   │
│   ├── services/
│   │   └── api.js
│   │
│   ├── context/
│   │   └── AuthContext.jsx
│   │
│   ├── routes/
│   │   └── AppRoutes.jsx
│   │
│   ├── App.jsx
│   └── main.jsx
│
├── package.json
└── README.md
```

Create reusable components wherever appropriate.

---

## 31. Backend Architecture

Use a clean layered structure.

### Accepted Architecture

For a 6–8 hour assignment, two patterns are equally acceptable:

**Full layered (preferred where time allows):**

```
Router → Service → Repository → Database
```

**Simplified (acceptable under time pressure):**

```
Router → Service → Database
```

Do not create unnecessary abstraction layers. The goal is correct, readable, maintainable code — not architectural complexity.

### Recommended Structure

```
backend/
├── app/
│   ├── main.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── dependencies.py
│   │
│   ├── db/
│   │   └── database.py
│   │
│   ├── models/
│   │   ├── user.py
│   │   ├── lead.py
│   │   ├── lead_note.py
│   │   ├── follow_up.py
│   │   ├── project.py
│   │   ├── building.py
│   │   ├── unit.py
│   │   └── booking.py
│   │
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── lead.py
│   │   ├── lead_note.py
│   │   ├── follow_up.py
│   │   ├── project.py
│   │   ├── building.py
│   │   ├── unit.py
│   │   └── booking.py
│   │
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── lead_service.py
│   │   ├── property_service.py
│   │   ├── booking_service.py
│   │   └── dashboard_service.py
│   │
│   └── routers/
│       ├── auth.py
│       ├── users.py
│       ├── leads.py
│       ├── projects.py
│       ├── buildings.py
│       ├── units.py
│       ├── bookings.py
│       └── dashboard.py
│
├── tests/
│   ├── test_auth.py
│   ├── test_leads.py
│   ├── test_properties.py
│   └── test_bookings.py
│
├── alembic/
├── requirements.txt
├── .env.example
└── README.md
```

A `repositories/` layer is optional and may be added if time permits.

---

## 32. API Organization

Base path: `/api`

API groups:

```
/api/auth
/api/users
/api/leads
/api/projects
/api/buildings
/api/units
/api/bookings
/api/dashboard
```

Use RESTful naming conventions throughout.

---

## 33. Pagination Response Format

All list endpoints must return a consistent pagination envelope:

```json
{
  "items": [ ...list of objects... ],
  "total": 120,
  "page": 1,
  "size": 10
}
```

Applicable endpoints:

* `GET /api/leads`
* `GET /api/users`
* `GET /api/projects`
* `GET /api/buildings/{building_id}/units`
* `GET /api/bookings`
* `GET /api/follow-ups`
* `GET /api/leads/{lead_id}/notes`
* `GET /api/leads/{lead_id}/follow-ups`

---

## 34. Validation Requirements

Backend validation is mandatory.

| Field | Rule |
|-------|------|
| Email | Valid email format |
| Phone | Reasonable digit count |
| Required fields | Must not be empty |
| Price / Amount | Must be ≥ 0 if provided |
| Unit number | Required, unique within building |
| Lead stage | Must be a valid enum value |
| Lead source | Must be a valid enum value |
| Unit type | Must be a valid enum value |
| Booking amount | Optional; if provided must be ≥ 0 |
| Follow-up date | Must not be in the past on creation |
| Referenced IDs | Referenced entities must exist |

---

## 35. Error Handling

Use consistent API error responses.

Standard format:

```json
{
  "detail": "Human-readable error message"
}
```

Examples:

```json
{ "detail": "Lead not found" }
{ "detail": "Unit A-101 is already booked" }
{ "detail": "You do not have permission to book this lead" }
{ "detail": "Follow-up date cannot be in the past" }
{ "detail": "Booking is not in CONFIRMED state" }
```

Do not expose stack traces or internal exception details in API responses.

---

## 36. Authorization

Authorization is enforced on the backend. Frontend route guards are UX convenience only — they do not replace backend checks.

Authorization is centralized through FastAPI dependency injection (e.g., `Depends(get_current_admin)`, `Depends(get_current_user)`).

Key rules:

* All property management (create/edit/delete projects, buildings, units) → Admin only
* User management → Admin only
* Booking cancellation → Admin only
* Lead assignment → Admin only
* Lead access for Sales → only their assigned leads
* Note deletion → own notes only for Sales; any note for Admin
* Dashboard metrics → role-scoped (see Section 27)

---

## 37. Complete Role-Permission Matrix

| Feature | Admin | Sales Employee |
|---------|-------|----------------|
| Login | ✅ | ✅ |
| View dashboard (all metrics) | ✅ | ❌ |
| View dashboard (own metrics only) | ✅ | ✅ |
| View all leads | ✅ | ❌ |
| View unassigned leads | ✅ | ❌ |
| View own assigned leads | ✅ | ✅ |
| Create lead | ✅ | ✅ |
| Edit any lead | ✅ | ❌ |
| Edit own assigned lead | ✅ | ✅ |
| Assign / reassign lead | ✅ | ❌ |
| Soft-delete lead | ✅ | ❌ |
| List all users | ✅ | ❌ |
| Create user | ✅ | ❌ |
| Edit user | ✅ | ❌ |
| Deactivate user | ✅ | ❌ |
| Create project | ✅ | ❌ |
| Edit / delete project | ✅ | ❌ |
| Create building | ✅ | ❌ |
| Edit / delete building | ✅ | ❌ |
| Create unit | ✅ | ❌ |
| Edit / delete unit | ✅ | ❌ |
| View units (read-only) | ✅ | ✅ |
| Create booking (any valid lead) | ✅ | ❌ |
| Create booking (own assigned lead) | ✅ | ✅ |
| Create booking (another's lead) | ✅ | ❌ → 403 |
| Cancel booking | ✅ | ❌ → 403 |
| View all bookings | ✅ | ❌ |
| View own bookings | ✅ | ✅ |
| Add note to assigned lead | ✅ | ✅ |
| Delete own note | ✅ | ✅ |
| Delete any note | ✅ | ❌ |
| Create follow-up (own leads) | ✅ | ✅ |
| Create follow-up (any lead) | ✅ | ❌ |
| View all follow-ups | ✅ | ❌ |
| View own follow-ups | ✅ | ✅ |
| Update follow-up status | ✅ | ✅ (own only) |

---

## 38. Database Migration

Use Alembic.

The project must include an `alembic/` directory.

The README must explain:

```bash
alembic upgrade head
```

Database schema must be reproducible from migrations. Manual table creation via pgAdmin must not be required.

The initial migration must include:

* All table definitions
* All enum types
* All foreign key constraints with correct ON DELETE behavior
* `UNIQUE(building_id, unit_number)` on units
* **`CREATE UNIQUE INDEX uix_unit_confirmed_booking ON bookings(unit_id) WHERE status = 'CONFIRMED'`** — this is mandatory
* All performance indexes listed in the relevant sections

---

## 39. Seed Data

Provide useful demo/seed data.

### Users

```
Admin:
  Email: admin@example.com
  Password: Admin@123
  Role: ADMIN

Sales Employee:
  Email: sales@example.com
  Password: Sales@123
  Role: SALES
```

Passwords must be bcrypt-hashed in the database.

### Seed Content

* At least 2 users (as above)
* At least 2 projects
* Multiple buildings per project
* Multiple units per building (mix of AVAILABLE and BOOKED)
* Multiple leads in different stages
* Follow-ups (PENDING and COMPLETED)
* At least one CONFIRMED booking
* At least one CANCELLED booking

The seeded data must make the dashboard immediately meaningful after login.

---

## 40. Testing Requirements

At minimum, test:

### Authentication

* Valid login returns JWT
* Invalid credentials return 401
* Protected endpoint without token returns 401

### Leads

* Create lead
* Retrieve leads (with pagination)
* Update lead
* Search and filter leads
* Sales employee cannot access another employee's lead

### Properties

* Create project, building, unit
* Retrieve units with status filter

### Booking — Highest Priority

* Successfully create booking
* Cannot book already-booked unit → 409
* Invalid lead → 404
* Invalid unit → 404
* Sales employee cannot book another's lead → 403
* Sales employee cannot cancel booking → 403
* Booking cancellation → unit returns to AVAILABLE
* Concurrent booking attempt produces exactly one success and one 409

---

## 41. UI/UX Requirements

The application must look like a professional internal CRM, not a basic CRUD demo.

Required UI elements:

* Responsive sidebar navigation
* Header with user info and logout
* Dashboard metric cards
* Tables with search and filters
* Pagination controls
* Forms with validation messages
* Loading states (spinner or skeleton) on all async operations
* Empty states when lists have no items
* Error states when API calls fail
* Confirmation dialogs for destructive actions (booking cancellation, lead deletion)
* Status badges (color-coded: AVAILABLE=green, BOOKED=red, stages with appropriate colors)
* Clear action buttons

Avoid unnecessary animations or complex visual effects. Focus on usability.

---

## 42. Responsive Design

The application must work reasonably on:

* Desktop
* Laptop
* Tablet
* Mobile

Tables must use horizontal scroll on small screens.
Forms must stack vertically on small screens.
Sidebar navigation must collapse to a menu on mobile.

---

## 43. Security Requirements

* Hash passwords with bcrypt. Never store plaintext.
* Use JWT for authentication.
* Check `is_active` on login — inactive users must be rejected.
* Do not commit `.env`. Provide `.env.example`.
* Validate all request data with Pydantic.
* Implement backend authorization checks (never rely on frontend alone).
* Do not expose passwords or password hashes in API responses.
* Do not expose internal exception details in API responses.
* Use SQLAlchemy ORM queries (parameterized) to prevent SQL injection.
* Enforce ownership/permission checks on all mutating operations.

---

## 44. Environment Configuration

Use environment variables.

`.env.example`:

```env
DATABASE_URL=postgresql+psycopg://postgres:password@localhost:5432/real_estate_crm

SECRET_KEY=change-this-secret

ACCESS_TOKEN_EXPIRE_MINUTES=60
```

Never commit real secrets. The `.env` file must be in `.gitignore`.

---

## 45. Complete API Summary

| Module      | Method | Endpoint                              | Admin | Sales |
| ----------- | ------ | ------------------------------------- | ----- | ----- |
| Auth        | POST   | `/api/auth/login`                     | ✅    | ✅    |
| Auth        | GET    | `/api/auth/me`                        | ✅    | ✅    |
| Users       | GET    | `/api/users`                          | ✅    | ❌    |
| Users       | POST   | `/api/users`                          | ✅    | ❌    |
| Users       | GET    | `/api/users/{id}`                     | ✅    | ❌    |
| Users       | PUT    | `/api/users/{id}`                     | ✅    | ❌    |
| Users       | PATCH  | `/api/users/{id}/deactivate`          | ✅    | ❌    |
| Leads       | POST   | `/api/leads`                          | ✅    | ✅    |
| Leads       | GET    | `/api/leads`                          | ✅    | ✅*   |
| Leads       | GET    | `/api/leads/{id}`                     | ✅    | ✅*   |
| Leads       | PUT    | `/api/leads/{id}`                     | ✅    | ✅*   |
| Leads       | DELETE | `/api/leads/{id}`                     | ✅    | ❌    |
| Notes       | POST   | `/api/leads/{id}/notes`               | ✅    | ✅*   |
| Notes       | GET    | `/api/leads/{id}/notes`               | ✅    | ✅*   |
| Notes       | DELETE | `/api/leads/{id}/notes/{note_id}`     | ✅    | ✅**  |
| Follow-ups  | POST   | `/api/leads/{id}/follow-ups`          | ✅    | ✅*   |
| Follow-ups  | GET    | `/api/leads/{id}/follow-ups`          | ✅    | ✅*   |
| Follow-ups  | PUT    | `/api/follow-ups/{id}`                | ✅    | ✅*   |
| Follow-ups  | GET    | `/api/follow-ups`                     | ✅    | ✅*   |
| Projects    | POST   | `/api/projects`                       | ✅    | ❌    |
| Projects    | GET    | `/api/projects`                       | ✅    | ✅    |
| Projects    | GET    | `/api/projects/{id}`                  | ✅    | ✅    |
| Projects    | PUT    | `/api/projects/{id}`                  | ✅    | ❌    |
| Projects    | DELETE | `/api/projects/{id}`                  | ✅    | ❌    |
| Buildings   | POST   | `/api/projects/{id}/buildings`        | ✅    | ❌    |
| Buildings   | GET    | `/api/projects/{id}/buildings`        | ✅    | ✅    |
| Buildings   | GET    | `/api/buildings/{id}`                 | ✅    | ✅    |
| Buildings   | PUT    | `/api/buildings/{id}`                 | ✅    | ❌    |
| Buildings   | DELETE | `/api/buildings/{id}`                 | ✅    | ❌    |
| Units       | POST   | `/api/buildings/{id}/units`           | ✅    | ❌    |
| Units       | GET    | `/api/buildings/{id}/units`           | ✅    | ✅    |
| Units       | GET    | `/api/units/{id}`                     | ✅    | ✅    |
| Units       | PUT    | `/api/units/{id}`                     | ✅    | ❌    |
| Units       | DELETE | `/api/units/{id}`                     | ✅    | ❌    |
| Bookings    | POST   | `/api/bookings`                       | ✅    | ✅*   |
| Bookings    | GET    | `/api/bookings`                       | ✅    | ✅*   |
| Bookings    | GET    | `/api/bookings/{id}`                  | ✅    | ✅*   |
| Bookings    | PATCH  | `/api/bookings/{id}/cancel`           | ✅    | ❌    |
| Dashboard   | GET    | `/api/dashboard/summary`              | ✅    | ✅*   |

`*` = restricted to own data (own leads, own bookings, own follow-ups)
`**` = restricted to own notes only

---

## 46. MVP Scope

### Must Have

* Login, JWT, Admin/Sales roles
* Leads: list, search, filter, create, edit, stage update, assignment, details, notes, follow-ups
* Properties: projects, buildings, units, availability
* Booking: Lead → Unit, transaction-safe, duplicate prevention, cancellation
* Dashboard: scoped metrics by role
* Responsive UI with loading/error/empty states
* Database migrations and seed data
* README

### Should Have

* Cascading booking form (Project → Building → Available Unit)
* Confirmation dialogs for destructive actions
* JWT expiry handling (redirect to login on 401)
* User management UI (Admin)

### Nice to Have

* Unit area (sq ft) field
* Audit trail for stage changes
* Date range filters on bookings
* Advanced dashboard charts

---

## 47. Features That Must Not Be Over-Engineered

Do not implement unless significant time remains:

* Microservices / service mesh
* Kubernetes / Docker orchestration
* Redis / caching layer
* Kafka / message queues
* Payment gateway
* Email / SMS notifications
* AI features
* Complex audit system
* Multi-tenant architecture

The objective is a polished, reliable, correct MVP.

---

## 48. Implementation Order

### Phase 1 — Project Setup (~30 min)

* Backend: FastAPI scaffold, `.env`, `requirements.txt`, Alembic init
* Frontend: Vite + React scaffold, Axios, Router, CSS framework
* PostgreSQL connection verified

### Phase 2 — Database (~45 min)

* All SQLAlchemy models with enums, relationships, constraints
* ON DELETE rules applied at model level
* Alembic initial migration
* Verify partial unique index `uix_unit_confirmed_booking` is in migration
* All performance indexes in migration

### Phase 3 — Authentication (~30 min)

* User model, bcrypt hashing, JWT encode/decode
* `POST /api/auth/login` with `is_active` check
* `GET /api/auth/me`
* Role-based FastAPI dependencies
* Seed data

### Phase 4 — Leads (~60 min)

* Full CRUD with soft-delete
* Stage update, assignment (Admin only)
* Pagination, search, filter
* Notes (append-only, own-delete rule)
* Follow-ups (create with past-date validation, list, update)

### Phase 5 — Properties (~45 min)

* Projects CRUD (Admin only)
* Buildings CRUD (Admin only)
* Units CRUD (Admin only) with enum type
* Availability filter

### Phase 6 — Booking (~60 min) ← HIGHEST PRIORITY

* Booking service with `SELECT FOR UPDATE`
* `POST /api/bookings` full transaction
* Permission check (Sales = own leads only)
* 409 from lock check + IntegrityError fallback
* Unit status update + Lead stage update in transaction
* `PATCH /api/bookings/{id}/cancel` with transaction
* Verify concurrent booking produces exactly one success

### Phase 7 — Dashboard (~20 min)

* `GET /api/dashboard/summary`
* Strict role-scoped queries

### Phase 8 — Frontend (~90 min)

* AuthContext + protected routes + login page
* Dashboard with metric cards
* Leads list (search/filter/pagination) + Lead Details
* Properties page (hierarchy drill-down)
* Bookings list
* Booking form (cascading selectors, 409 error display)

### Phase 9 — Integration & Polish (~30 min)

* Connect all frontend pages to API
* Loading, empty, error states on all pages
* Responsive layout verification

### Phase 10 — Testing (~30 min)

* `test_auth.py`
* `test_bookings.py` (including concurrent booking test)
* `test_leads.py`

### Phase 11 — Documentation (~15 min)

* README with full setup instructions
* Demo credentials
* Design decisions
* Swagger/OpenAPI auto-docs

---

## 49. Definition of Done

The project is considered complete when:

* [ ] Admin can login.
* [ ] Sales employee can login.
* [ ] Inactive user cannot login.
* [ ] JWT authentication works.
* [ ] Role-based authorization works.
* [ ] Leads can be created, edited, searched, filtered.
* [ ] Lead assignment (Admin only) works.
* [ ] Lead stages work correctly.
* [ ] Notes are append-only; own-note deletion works.
* [ ] Follow-ups work with past-date validation.
* [ ] Projects, buildings, units can be managed (Admin).
* [ ] Unit type uses controlled enum.
* [ ] Lead source uses controlled enum.
* [ ] Unit availability is displayed.
* [ ] Booking connects a lead to a unit.
* [ ] Duplicate booking is prevented (409 on second attempt).
* [ ] `SELECT FOR UPDATE` is used in booking creation.
* [ ] Partial unique index `uix_unit_confirmed_booking` exists in DB.
* [ ] Booking cancellation is transaction-safe.
* [ ] Unit status changes correctly on booking and cancellation.
* [ ] Lead stage changes to BOOKED on booking creation.
* [ ] Sales employee cannot book another employee's lead (403).
* [ ] Sales employee cannot cancel a booking (403).
* [ ] Dashboard shows correct scoped metrics per role.
* [ ] Frontend booking form uses cascading selectors.
* [ ] Frontend shows 409 conflict message correctly.
* [ ] User deactivation works; deactivated users cannot log in.
* [ ] ON DELETE behaviors match specification.
* [ ] Pagination envelope `{items, total, page, size}` used on all list endpoints.
* [ ] Frontend is responsive.
* [ ] Loading, empty, and error states exist on all pages.
* [ ] API validation works (Pydantic).
* [ ] Backend authorization works (not just frontend).
* [ ] Database migrations run from scratch with `alembic upgrade head`.
* [ ] Seed data provides meaningful demo state.
* [ ] Tests cover auth, leads, booking (including concurrent test).
* [ ] README is complete with setup, credentials, and design decisions.
* [ ] GitHub repository is clean and runnable.

---

## 50. Final Product Flow

```
LOGIN
  ↓
DASHBOARD (role-scoped metrics)
  ↓
LEADS LIST
  ↓
Create / Assign Lead
  ↓
Contact Customer → stage = CONTACTED
  ↓
Schedule Site Visit → stage = SITE_VISIT
  ↓
Customer Shows Interest → stage = INTERESTED
  ↓
Price Discussion → stage = NEGOTIATION
  ↓
SELECT PROPERTY
  (Project → Building → Available Unit)
  ↓
CREATE BOOKING
  ↓
  BEGIN TRANSACTION
    ↓
  SELECT unit FOR UPDATE
    ↓
  unit.status == AVAILABLE?
    ├── NO  → ROLLBACK → HTTP 409 "Unit already booked"
    └── YES → INSERT booking (status=CONFIRMED, booking_date=NOW())
              → UPDATE unit.status = BOOKED
              → UPDATE lead.stage = BOOKED
              → COMMIT
  ↓
BOOKING SUCCESS
  ↓
Lead stage = BOOKED, Unit = BOOKED, Booking = CONFIRMED
```

If a concurrent attempt is made:

```
Second request → SELECT unit FOR UPDATE
  → Blocked until first transaction commits
  → Reads unit.status = BOOKED
  → ROLLBACK
  → HTTP 409 "Unit A-101 is already booked"
  → Frontend: "This unit was just booked by someone else. Please select another unit."
```

This behavior is mandatory and must be verified by tests.
