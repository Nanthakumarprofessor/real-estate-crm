# Real Estate CRM — Software Design Specification

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

# 2. Recommended Technology Stack

## Backend

* Python 3.11+
* FastAPI
* SQLAlchemy 2.x
* PostgreSQL
* Pydantic v2
* JWT authentication
* Passlib/bcrypt or an appropriate password hashing library
* Alembic for database migrations
* Pytest for testing
* FastAPI OpenAPI/Swagger documentation

## Frontend

* React
* Vite
* React Router
* Axios
* Bootstrap or Tailwind CSS

The frontend should be responsive and professional.

## Development Tools

* Git
* GitHub
* VS Code/Kiro
* Postman or Swagger UI

---

# 3. User Roles

The application has two roles.

## 3.1 Admin

Admin users can:

* Login
* View dashboard
* View all leads
* Create/edit/delete leads
* Assign leads to sales employees
* View all sales employees
* Create/manage projects
* Create/manage buildings
* Create/manage units
* View all bookings
* Create bookings where permitted
* Cancel bookings
* View system-wide metrics

## 3.2 Sales Employee

Sales employees can:

* Login
* View dashboard relevant to their work
* View leads assigned to them
* Create leads
* Edit their assigned leads
* Update lead stages
* Add notes
* Manage follow-ups
* View available properties/units
* Create bookings for permitted leads
* View their bookings

Sales employees should not be able to perform Admin-only operations such as managing users or deleting arbitrary users.

---

# 4. Authentication

Authentication must use JWT.

## Login

### Endpoint

POST `/api/auth/login`

### Request

```json
{
  "email": "admin@example.com",
  "password": "Admin@123"
}
```

### Response

```json
{
  "access_token": "<jwt-token>",
  "token_type": "bearer"
}
```

The JWT should contain enough information to identify the authenticated user and role.

Protected endpoints must require:

```text
Authorization: Bearer <token>
```

## Current User

GET `/api/auth/me`

Returns the currently authenticated user.

Example:

```json
{
  "id": 1,
  "name": "Admin User",
  "email": "admin@example.com",
  "role": "ADMIN"
}
```

---

# 5. Lead Management

A Lead represents a potential customer interested in purchasing a property.

## Lead Stages

The following stages must be supported:

```text
NEW
CONTACTED
SITE_VISIT
INTERESTED
NEGOTIATION
BOOKED
LOST
```

## Example Business Flow

A customer named Rahul contacts the real-estate company.

Initially:

```text
Rahul → NEW
```

Sales employee contacts Rahul:

```text
Rahul → CONTACTED
```

Rahul agrees to visit the property:

```text
Rahul → SITE_VISIT
```

Rahul likes Unit A-101:

```text
Rahul → INTERESTED
```

Price negotiation starts:

```text
Rahul → NEGOTIATION
```

Rahul agrees to purchase A-101:

```text
Rahul → BOOKED
```

The system then creates a booking connecting:

```text
Rahul (Lead)
       ↓
   Booking
       ↓
Unit A-101
```

---

# 6. Lead Database Model

Table: `leads`

Fields:

| Field       | Type         | Description             |
| ----------- | ------------ | ----------------------- |
| id          | UUID/Integer | Primary key             |
| name        | String       | Customer name           |
| email       | String       | Customer email          |
| phone       | String       | Customer phone          |
| source      | String       | Lead source             |
| stage       | Enum         | Current lead stage      |
| assigned_to | FK           | Assigned sales employee |
| is_active   | Boolean      | Soft-delete flag        |
| created_at  | DateTime     | Creation timestamp      |
| updated_at  | DateTime     | Last update timestamp   |

Lead stage should use an enum rather than arbitrary strings.

---

# 7. Lead APIs

## Create Lead

POST `/api/leads`

Example:

```json
{
  "name": "Rahul Kumar",
  "email": "rahul@example.com",
  "phone": "9876543210",
  "source": "Website",
  "stage": "NEW",
  "assigned_to": 2
}
```

## List Leads

GET `/api/leads`

Support:

* Pagination
* Search
* Stage filtering
* Assigned employee filtering

Example:

```text
GET /api/leads?page=1&size=10
GET /api/leads?search=Rahul
GET /api/leads?stage=NEGOTIATION
GET /api/leads?assigned_to=2
```

## Get Lead

GET `/api/leads/{id}`

## Update Lead

PUT `/api/leads/{id}`

## Delete Lead

DELETE `/api/leads/{id}`

Prefer soft deletion using `is_active=false`.

---

# 8. Lead Notes

Sales employees should be able to add notes to leads.

Example:

```text
Customer interested in 2BHK.
Requested site visit on Saturday.
```

## Database Model

Table: `lead_notes`

Fields:

| Field      | Type       |
| ---------- | ---------- |
| id         | PK         |
| lead_id    | FK → leads |
| user_id    | FK → users |
| note       | Text       |
| created_at | DateTime   |

## APIs

POST `/api/leads/{lead_id}/notes`

GET `/api/leads/{lead_id}/notes`

DELETE `/api/leads/{lead_id}/notes/{note_id}`

---

# 9. Follow-Ups

Sales employees need to track upcoming customer follow-ups.

Table: `follow_ups`

Fields:

| Field        | Type       |
| ------------ | ---------- |
| id           | PK         |
| lead_id      | FK → leads |
| assigned_to  | FK → users |
| follow_up_at | DateTime   |
| notes        | Text       |
| status       | Enum       |
| created_at   | DateTime   |
| updated_at   | DateTime   |

Follow-up statuses:

```text
PENDING
COMPLETED
CANCELLED
```

## APIs

Create:

POST `/api/leads/{lead_id}/follow-ups`

List:

GET `/api/leads/{lead_id}/follow-ups`

Update:

PUT `/api/follow-ups/{id}`

Upcoming follow-ups:

GET `/api/follow-ups?status=PENDING`

---

# 10. Property Management

The property hierarchy is:

```text
Project
   ↓
Building
   ↓
Unit
```

Example:

```text
ABC Residency
    |
    +── Tower A
    |      |
    |      +── A-101
    |      +── A-102
    |      +── A-103
    |
    +── Tower B
           |
           +── B-101
           +── B-102
```

---

# 11. Projects

Table: `projects`

Fields:

| Field       | Type     |
| ----------- | -------- |
| id          | PK       |
| name        | String   |
| location    | String   |
| description | Text     |
| created_at  | DateTime |
| updated_at  | DateTime |

## APIs

POST `/api/projects`

GET `/api/projects`

GET `/api/projects/{id}`

PUT `/api/projects/{id}`

DELETE `/api/projects/{id}`

---

# 12. Buildings

Table: `buildings`

Fields:

| Field        | Type          |
| ------------ | ------------- |
| id           | PK            |
| project_id   | FK → projects |
| name         | String        |
| total_floors | Integer       |
| created_at   | DateTime      |
| updated_at   | DateTime      |

Relationship:

```text
Project 1 ─────── N Buildings
```

## APIs

POST `/api/projects/{project_id}/buildings`

GET `/api/projects/{project_id}/buildings`

GET `/api/buildings/{id}`

PUT `/api/buildings/{id}`

DELETE `/api/buildings/{id}`

---

# 13. Units

Table: `units`

Fields:

| Field       | Type           |
| ----------- | -------------- |
| id          | PK             |
| building_id | FK → buildings |
| unit_number | String         |
| type        | String         |
| floor       | Integer        |
| price       | Decimal        |
| status      | Enum           |
| created_at  | DateTime       |
| updated_at  | DateTime       |

Unit status:

```text
AVAILABLE
BOOKED
```

A building must not contain duplicate unit numbers.

Database constraint:

```text
UNIQUE(building_id, unit_number)
```

Example:

```text
Tower A + A-101 → unique
Tower A + A-102 → unique
Tower B + B-101 → unique
```

---

# 14. Unit APIs

Create:

POST `/api/buildings/{building_id}/units`

List:

GET `/api/buildings/{building_id}/units`

Support filters:

```text
status=AVAILABLE
status=BOOKED
type=2BHK
```

Get:

GET `/api/units/{id}`

Update:

PUT `/api/units/{id}`

Delete:

DELETE `/api/units/{id}`

---

# 15. Booking Management

Booking is the most important business operation in this application.

A booking connects:

```text
Lead → Unit → User
```

Example:

```text
Lead:
Rahul Kumar

Unit:
Tower A / A-101

Booked By:
Sales Employee
```

---

# 16. Booking Database Model

Table: `bookings`

Fields:

| Field        | Type       |
| ------------ | ---------- |
| id           | PK         |
| lead_id      | FK → leads |
| unit_id      | FK → units |
| booked_by    | FK → users |
| booking_date | DateTime   |
| amount       | Decimal    |
| status       | Enum       |
| created_at   | DateTime   |
| updated_at   | DateTime   |

Booking status:

```text
CONFIRMED
CANCELLED
```

---

# 17. Critical Business Rule — No Duplicate Bookings

The same property unit must never be booked by two different customers at the same time.

For example:

```text
Customer A → Unit A-101 → BOOKED
```

If another employee attempts:

```text
Customer B → Unit A-101 → BOOKED
```

the system must reject the request.

Expected response:

HTTP `409 Conflict`

Example:

```json
{
  "detail": "Unit A-101 is already booked"
}
```

This rule must be enforced at the **database/transaction level**, not only in frontend code.

---

# 18. Concurrency-Safe Booking

The booking operation must be transaction-safe.

A simple check such as:

```python
if unit.status == "AVAILABLE":
    create_booking()
```

is NOT sufficient because two requests can execute simultaneously.

Example:

```text
Request A → checks A-101 → AVAILABLE
Request B → checks A-101 → AVAILABLE

Request A → creates booking
Request B → creates booking
```

This creates a race condition.

The backend must prevent this.

Recommended approach:

1. Begin database transaction.
2. Lock the unit row using PostgreSQL row-level locking.
3. Re-check unit availability.
4. If already booked, return `409 Conflict`.
5. Create booking.
6. Update unit status to `BOOKED`.
7. Update lead stage to `BOOKED`.
8. Commit transaction.

SQLAlchemy/PostgreSQL row locking can use:

```text
SELECT ... FOR UPDATE
```

Additionally, enforce database-level uniqueness for active bookings wherever practical.

The database must be considered the final authority for booking consistency.

---

# 19. Create Booking API

POST `/api/bookings`

Request:

```json
{
  "lead_id": 1,
  "unit_id": 5,
  "amount": 250000
}
```

The backend should:

1. Authenticate user.
2. Validate the lead.
3. Validate the unit.
4. Validate permissions.
5. Start a transaction.
6. Lock the unit row.
7. Check availability.
8. Create booking.
9. Change unit status to `BOOKED`.
10. Change lead stage to `BOOKED`.
11. Commit transaction.

Successful response:

HTTP `201 Created`

```json
{
  "id": 10,
  "lead_id": 1,
  "unit_id": 5,
  "booked_by": 2,
  "amount": 250000,
  "status": "CONFIRMED"
}
```

Already booked:

HTTP `409 Conflict`

```json
{
  "detail": "Unit A-101 is already booked"
}
```

---

# 20. Booking APIs

Create:

POST `/api/bookings`

List:

GET `/api/bookings`

Get:

GET `/api/bookings/{id}`

Cancel:

PATCH `/api/bookings/{id}/cancel`

When a confirmed booking is cancelled, the implementation may make the unit available again if that matches the application's business rules.

Recommended MVP behavior:

```text
CONFIRMED booking
        ↓
CANCELLED
        ↓
Unit → AVAILABLE
```

Ensure this operation is also transaction-safe.

---

# 21. Booking Validation

Before creating a booking:

* Lead must exist.
* Lead must be active.
* Unit must exist.
* Unit must be active.
* Unit must be available.
* User must have permission.
* Amount must be valid if supplied.
* A confirmed booking must not already exist for the unit.

Possible HTTP responses:

```text
400 Bad Request
401 Unauthorized
403 Forbidden
404 Not Found
409 Conflict
422 Unprocessable Entity
500 Internal Server Error
```

Use appropriate status codes rather than returning HTTP 200 for errors.

---

# 22. Users Database Model

Table: `users`

Fields:

| Field         | Type          |
| ------------- | ------------- |
| id            | PK            |
| name          | String        |
| email         | String UNIQUE |
| password_hash | String        |
| role          | Enum          |
| is_active     | Boolean       |
| created_at    | DateTime      |
| updated_at    | DateTime      |

Roles:

```text
ADMIN
SALES
```

Passwords must never be stored as plain text.

---

# 23. Database Relationships

Main relationships:

```text
USERS
  │
  ├──────────────< LEADS
  │                  │
  │                  ├────────< LEAD_NOTES
  │                  │
  │                  └────────< FOLLOW_UPS
  │
  └──────────────< BOOKINGS


PROJECTS
  │
  └──────────────< BUILDINGS
                       │
                       └──────────────< UNITS
                                             │
                                             └────── BOOKING


LEADS
  │
  └──────────────< BOOKINGS
```

Detailed cardinality:

```text
User 1 ─── N Leads
User 1 ─── N LeadNotes
User 1 ─── N FollowUps
User 1 ─── N Bookings

Lead 1 ─── N LeadNotes
Lead 1 ─── N FollowUps
Lead 1 ─── N Bookings

Project 1 ─── N Buildings
Building 1 ─── N Units

Unit 1 ─── 0..1 active Booking
```

---

# 24. Dashboard

Create:

GET `/api/dashboard/summary`

The dashboard should provide meaningful sales information.

Example response:

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

For Sales Employees, dashboard metrics may be restricted to their assigned leads/bookings.

For Admins, show system-wide metrics.

---

# 25. Frontend Pages

The frontend should contain the following main pages.

## Login

Route:

```text
/login
```

Features:

* Email
* Password
* Login button
* Validation
* Error message

---

## Dashboard

Route:

```text
/dashboard
```

Display cards such as:

```text
Total Leads
New Leads
Negotiations
Bookings
Available Units
Upcoming Follow-ups
```

Use charts or visual summaries only where they add value.

---

## Leads

Route:

```text
/leads
```

Features:

* Lead table
* Search
* Stage filter
* Assigned employee filter
* Pagination
* Create lead
* Edit lead
* View lead details

---

## Lead Details

Route:

```text
/leads/:id
```

Show:

* Customer information
* Current stage
* Assigned employee
* Notes
* Follow-ups
* Booking information if applicable

Allow:

* Stage update
* Add note
* Create follow-up
* Edit lead

---

## Properties

Route:

```text
/properties
```

Display:

```text
Projects
    ↓
Buildings
    ↓
Units
```

Unit list should clearly show:

```text
Unit Number
Type
Floor
Price
Status
```

Available and booked units should be visually distinguishable.

---

## Bookings

Route:

```text
/bookings
```

Display:

* Lead
* Project
* Building
* Unit
* Amount
* Booking date
* Status
* Booked by

---

# 26. Booking UI

The booking form should allow the user to select:

```text
Lead
Project
Building
Available Unit
Amount
```

Only available units should normally be selectable.

However, the frontend availability check is only a UX improvement.

The backend must still enforce the rule.

If another user books the unit before submission:

```text
Frontend → POST /api/bookings
Backend → 409 Conflict
Frontend → display "Unit is already booked"
```

Do not rely on frontend state for business-critical consistency.

---

# 27. Frontend Architecture

Recommended structure:

```text
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

# 28. Backend Architecture

Use a clean layered structure.

Recommended:

```text
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
│   │   ├── database.py
│   │   └── models/
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
│   ├── repositories/
│   │   ├── user_repository.py
│   │   ├── lead_repository.py
│   │   ├── property_repository.py
│   │   └── booking_repository.py
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

Do not create unnecessary layers if they make the code harder to understand.

The architecture should remain appropriate for a small MVP.

---

# 29. API Organization

Use the following base path:

```text
/api
```

API groups:

```text
/api/auth
/api/users
/api/leads
/api/projects
/api/buildings
/api/units
/api/bookings
/api/dashboard
```

Use RESTful naming conventions.

---

# 30. Validation Requirements

Backend validation is mandatory.

Examples:

### Email

Must be a valid email format.

### Phone

Should contain a reasonable number of digits.

### Required fields

Required fields must not accept empty values.

### Price

Must be greater than or equal to zero.

### Unit number

Required and unique within a building.

### Lead stage

Must be one of the predefined enum values.

### Booking amount

Must not be negative.

### IDs

Referenced entities must exist.

---

# 31. Error Handling

Use consistent API error responses.

Example:

```json
{
  "detail": "Lead not found"
}
```

For duplicate booking:

```json
{
  "detail": "Unit A-101 is already booked"
}
```

Frontend should show meaningful user-friendly messages.

Do not expose stack traces or sensitive internal information to users.

---

# 32. Authorization

Authorization must be implemented on the backend.

Never rely only on frontend route protection.

Example:

```text
ADMIN
  ↓
Can manage users

SALES
  ↓
Cannot manage users
```

For lead access:

```text
ADMIN
  ↓
Can view all leads

SALES
  ↓
Normally works with assigned leads
```

The exact authorization logic should be centralized through FastAPI dependencies/services rather than duplicated throughout every route.

---

# 33. Database Migration

Use Alembic.

The project should include:

```text
alembic/
```

The README should explain:

```bash
alembic upgrade head
```

Database schema should be reproducible from migrations.

Do not require manually creating tables through pgAdmin.

---

# 34. Seed Data

The application should provide useful demo/seed data.

Create at least:

## Admin

```text
Email: admin@example.com
Password: Admin@123
Role: ADMIN
```

## Sales Employee

```text
Email: sales@example.com
Password: Sales@123
Role: SALES
```

Do not store passwords as plaintext in the database.

The credentials above are development/demo credentials only.

Seed:

* At least 2 users
* At least 2 projects
* Multiple buildings
* Multiple units
* Multiple leads
* Different lead stages
* Follow-ups
* At least one booking

The seeded data should make the dashboard immediately meaningful after login.

---

# 35. Testing Requirements

At minimum, test:

## Authentication

* Valid login
* Invalid login
* Protected endpoint without token

## Leads

* Create lead
* Retrieve leads
* Update lead
* Search/filter leads
* Authorization

## Properties

* Create project
* Create building
* Create unit
* Retrieve units
* Filter available units

## Booking

Most importantly:

* Successfully create booking
* Cannot book already booked unit
* Invalid lead
* Invalid unit
* Unauthorized booking
* Booking cancellation
* Unit availability changes correctly

## Concurrency

The booking flow should include a test or implementation verification demonstrating that concurrent attempts cannot create two confirmed bookings for the same unit.

---

# 36. Important Booking Scenario

The implementation must handle this scenario correctly.

Initial state:

```text
Unit A-101
Status = AVAILABLE
```

Two sales employees submit booking requests nearly simultaneously.

```text
Sales Employee 1 → Customer Rahul → A-101

Sales Employee 2 → Customer Arjun → A-101
```

Expected result:

```text
Request 1 → SUCCESS
Request 2 → 409 CONFLICT
```

Final database state:

```text
Unit A-101 → BOOKED

Confirmed Bookings:
1
```

There must never be:

```text
Unit A-101 → BOOKED

Confirmed Bookings:
2
```

This is a critical acceptance criterion.

---

# 37. UI/UX Requirements

The application should look like a professional internal CRM rather than a basic CRUD demo.

Include:

* Responsive layout
* Sidebar/navigation
* Header
* Dashboard cards
* Tables
* Search
* Filters
* Pagination
* Forms
* Validation messages
* Loading states
* Empty states
* Error states
* Confirmation dialogs where appropriate
* Status badges
* Clear action buttons

Avoid unnecessary animations or complicated visual effects.

Focus on usability.

---

# 38. Responsive Design

The application should work reasonably on:

```text
Desktop
Laptop
Tablet
Mobile
```

Tables should remain usable on smaller screens.

Forms should not overflow the viewport.

---

# 39. Security Considerations

Minimum security requirements:

* Hash passwords.
* Use JWT authentication.
* Do not commit `.env`.
* Provide `.env.example`.
* Validate request data.
* Implement backend authorization.
* Avoid exposing passwords.
* Avoid exposing internal exception details.
* Use parameterized ORM queries.
* Validate ownership/permissions where applicable.

---

# 40. Environment Configuration

Use environment variables.

Example `.env.example`:

```env
DATABASE_URL=postgresql+psycopg://postgres:password@localhost:5432/real_estate_crm

SECRET_KEY=change-this-secret

ACCESS_TOKEN_EXPIRE_MINUTES=60
```

Never commit real secrets.

---

# 41. README Requirements

The final repository must contain a useful README.

Include:

## Project Overview

What the CRM does.

## Features

* Authentication
* Role-based access
* Lead management
* Follow-ups
* Property management
* Booking
* Duplicate booking prevention
* Dashboard

## Technology Stack

List frontend, backend, database and tools.

## Architecture

Brief explanation of the architecture.

## Database

Explain the major tables and relationships.

## API

Provide important endpoint groups.

## Setup

Explain:

1. Clone repository
2. Create Python virtual environment
3. Install dependencies
4. Configure `.env`
5. Create PostgreSQL database
6. Run migrations
7. Seed data
8. Start backend
9. Start frontend

## Demo Credentials

Provide development credentials.

## Design Decisions

Include 3–5 important decisions.

Example:

1. PostgreSQL was selected because the application has strongly relational data.
2. JWT was selected for stateless API authentication.
3. Database transactions/row locking are used for booking consistency.
4. Soft deletion is used for leads.
5. FastAPI provides validation and OpenAPI documentation.

---

# 42. Suggested API Summary

| Module     | Method | Endpoint                       |
| ---------- | ------ | ------------------------------ |
| Auth       | POST   | `/api/auth/login`              |
| Auth       | GET    | `/api/auth/me`                 |
| Users      | GET    | `/api/users`                   |
| Users      | POST   | `/api/users`                   |
| Leads      | POST   | `/api/leads`                   |
| Leads      | GET    | `/api/leads`                   |
| Leads      | GET    | `/api/leads/{id}`              |
| Leads      | PUT    | `/api/leads/{id}`              |
| Leads      | DELETE | `/api/leads/{id}`              |
| Notes      | POST   | `/api/leads/{id}/notes`        |
| Notes      | GET    | `/api/leads/{id}/notes`        |
| Follow-ups | POST   | `/api/leads/{id}/follow-ups`   |
| Follow-ups | GET    | `/api/follow-ups`              |
| Projects   | POST   | `/api/projects`                |
| Projects   | GET    | `/api/projects`                |
| Buildings  | POST   | `/api/projects/{id}/buildings` |
| Buildings  | GET    | `/api/projects/{id}/buildings` |
| Units      | POST   | `/api/buildings/{id}/units`    |
| Units      | GET    | `/api/buildings/{id}/units`    |
| Bookings   | POST   | `/api/bookings`                |
| Bookings   | GET    | `/api/bookings`                |
| Bookings   | GET    | `/api/bookings/{id}`           |
| Bookings   | PATCH  | `/api/bookings/{id}/cancel`    |
| Dashboard  | GET    | `/api/dashboard/summary`       |

---

# 43. MVP Scope

Because the assignment has a 6–8 hour limit, prioritize the following.

## Must Have

### Authentication

* Login
* JWT
* Admin/Sales roles

### Leads

* List
* Search
* Filter
* Create
* Edit
* Stage update
* Assignment
* Details
* Notes
* Follow-ups

### Properties

* Projects
* Buildings
* Units
* Availability

### Booking

* Lead → Unit booking
* Backend validation
* Transaction-safe booking
* Duplicate booking prevention
* Booking list
* Cancellation

### Dashboard

* Lead metrics
* Unit metrics
* Booking metrics
* Follow-ups

### UI

* Responsive
* Professional
* Loading/error/empty states

---

# 44. Features That Should NOT Be Over-Engineered

Do not implement unless there is significant remaining time:

* Microservices
* Kubernetes
* Redis
* Kafka
* RabbitMQ
* Terraform
* Complex event-driven architecture
* Payment gateway
* Email/SMS notifications
* Advanced analytics
* AI chatbot
* Complex audit system
* Multi-tenant architecture
* Complex deployment infrastructure

The objective is a polished and reliable MVP.

---

# 45. Implementation Order

Implement in this order:

## Phase 1 — Project Setup

* Backend setup
* Frontend setup
* PostgreSQL connection
* Environment configuration

## Phase 2 — Database

* Models
* Relationships
* Enums
* Constraints
* Alembic migrations

## Phase 3 — Authentication

* User model
* Password hashing
* Login
* JWT
* Role dependencies

## Phase 4 — Leads

* CRUD
* Search
* Filters
* Assignment
* Notes
* Follow-ups

## Phase 5 — Properties

* Projects
* Buildings
* Units
* Availability

## Phase 6 — Booking

* Booking model
* Booking API
* Transaction
* Row locking
* Duplicate prevention
* Unit status update
* Lead stage update

## Phase 7 — Dashboard

* Summary API
* Dashboard UI

## Phase 8 — Frontend Integration

* Login
* Leads
* Properties
* Booking
* Dashboard

## Phase 9 — Testing

Test critical APIs and booking concurrency.

## Phase 10 — Documentation

* README
* API documentation
* Screenshots
* Design decisions

---

# 46. Definition of Done

The project is considered complete when:

* [ ] Admin can login.
* [ ] Sales employee can login.
* [ ] JWT authentication works.
* [ ] Role-based authorization works.
* [ ] Leads can be created.
* [ ] Leads can be edited.
* [ ] Leads can be searched.
* [ ] Leads can be filtered.
* [ ] Leads can be assigned.
* [ ] Lead stages work.
* [ ] Notes work.
* [ ] Follow-ups work.
* [ ] Projects can be managed.
* [ ] Buildings can be managed.
* [ ] Units can be managed.
* [ ] Unit availability is displayed.
* [ ] Booking connects a lead to a unit.
* [ ] Duplicate booking is prevented.
* [ ] Booking uses a transaction-safe implementation.
* [ ] Unit status changes correctly.
* [ ] Lead stage changes to BOOKED.
* [ ] Booking cancellation works.
* [ ] Dashboard displays meaningful metrics.
* [ ] Frontend is responsive.
* [ ] Loading states exist.
* [ ] Empty states exist.
* [ ] Error states exist.
* [ ] API validation works.
* [ ] Backend authorization works.
* [ ] Database migrations work.
* [ ] Seed/demo data exists.
* [ ] Tests cover critical business logic.
* [ ] README is complete.
* [ ] GitHub repository is clean and runnable.

---

# 47. Important Instructions for Kiro

This document is the source of truth for implementation.

Before writing significant amounts of code:

1. Analyze this specification.
2. Identify ambiguities or missing requirements.
3. Propose the final architecture.
4. Propose the database schema and relationships.
5. Confirm the API contracts.
6. Confirm the booking transaction strategy.
7. Confirm role/permission rules.
8. Break implementation into small tasks.

Do not blindly generate the entire application in one step.

Implement incrementally.

After each major phase:

* Run the application.
* Run relevant tests.
* Check API behavior.
* Fix issues before continuing.

The booking workflow is the highest-priority business rule.

The implementation must guarantee that two concurrent requests cannot successfully book the same unit.

Use PostgreSQL transaction semantics and database constraints where appropriate.

Keep the code clean, readable, maintainable and appropriately sized for a small production-minded MVP.

Do not introduce unnecessary technologies or architecture.

The final result should demonstrate:

```text
Good Engineering
        +
Correct Business Logic
        +
Reliable Database Design
        +
Professional UI/UX
        +
Clear Documentation
```

---

# 48. Final Product Flow

The final application should support this complete flow:

```text
LOGIN
  ↓
DASHBOARD
  ↓
LEADS
  ↓
Create / Assign Lead
  ↓
Contact Customer
  ↓
Update Stage
  ↓
SITE VISIT
  ↓
INTERESTED
  ↓
NEGOTIATION
  ↓
Select Property
  ↓
Select Available Unit
  ↓
CREATE BOOKING
  ↓
DATABASE TRANSACTION
  ↓
Check Unit Availability
  ↓
Lock Unit
  ↓
Create Booking
  ↓
Unit = BOOKED
  ↓
Lead = BOOKED
  ↓
COMMIT
  ↓
BOOKING SUCCESS
```

If another employee attempts to book the same unit:

```text
CREATE BOOKING
      ↓
LOCK UNIT
      ↓
Unit already BOOKED
      ↓
409 CONFLICT
      ↓
"Unit A-101 is already booked"
```

This behavior is mandatory.
