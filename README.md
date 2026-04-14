# Distributor API

Asynchronous REST API for organizing educational distribution between students and teachers.

Stack:

- FastAPI
- SQLAlchemy (async)
- PostgreSQL + asyncpg
- Pydantic
- Uvicorn
- JWT (role-based auth)

## Run

1. Create and activate virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and update PostgreSQL credentials.
4. Start API:

```bash
uvicorn app.main:app --reload
```

5. Apply migrations:

```bash
alembic upgrade head
```

6. Seed demo data:

```bash
python -m app.infrastructure.db.seed_demo
```

7. Run tests:

```bash
pytest -q
```

Current integration coverage includes:

- booking lifecycle (create, list, cancel)
- role authorization matrix (Student/Teacher/Admin route access)

## Main Endpoints

### Auth and Roles

Base prefix: `/api/v1/auth`

- `POST /bootstrap-admin` - one-time admin initialization (if no admins exist)
- `POST /register/student` - register student account and return bearer token
- `POST /register/teacher` - create teacher account (admin only)
- `POST /login` - login and receive bearer token
- `GET /me` - current authenticated account
- `GET /accounts` - list all accounts (admin only)

### Enrollment

Base prefix: `/api/v1/enrollment`

- `POST /cities` - create city (admin only)
- `GET /cities` - list cities
- `POST /disciplines` - create discipline (admin only)
- `GET /disciplines` - list disciplines
- `POST /teachers` - create teacher and assign disciplines (admin only)
- `GET /teachers?city_id=&discipline_id=` - filter teachers
- `POST /students` - create student profile (admin only)
- `GET /students?city_id=&email=` - list students and find profile by email (admin only)
- `POST /slots` - create teacher slot for discipline (admin only)
- `GET /slots/available?city_id=&discipline_id=&teacher_id=` - list available slots only
- `POST /bookings` - book slot (student/admin; student is limited to own profile)
- `GET /bookings?student_id=` - list bookings (student/admin; student sees only own)
- `DELETE /bookings/{booking_id}` - cancel booking (student/admin; student can cancel only own)

### Teacher Slot Management

Base prefix: `/api/v1/teacher/slots` (teacher role)

- `GET /` - list teacher's own slots with reserved/available seats
- `POST /` - create new slot for authenticated teacher
- `PUT /{slot_id}` - update own slot
- `DELETE /{slot_id}` - delete own slot

## Demo Credentials (seed)

- Admin: `admin / admin12345`
- Teachers:
  - `teacher_ivan / teacher123`
  - `teacher_olena / teacher123`
  - `teacher_maria / teacher123`
- Students:
  - `student_andriy / student123`
  - `student_iryna / student123`
  - `student_taras / student123`

## Frontend (React)

Frontend project is available in `frontend`.

1. Open `frontend/.env.example` and copy values to `.env`.
2. Start frontend:

```bash
cd frontend
npm run dev
```

3. Build frontend:

```bash
cd frontend
npm run build
```

The frontend now supports:

- login by role
- student booking dashboard
- teacher slot management screen (create, update, activate/deactivate, delete)
- admin panel for teacher-account provisioning

## Docker Compose (One Command)

Run backend + postgres + frontend:

```bash
docker compose up --build
```

Services:

- Backend API: `http://localhost:8000`
- Frontend: `http://localhost:5173`
- PostgreSQL: `localhost:5432`

## Notes

- `DB_INIT_ON_STARTUP=false` is recommended for migration-first workflow.
- For production/staging, prefer Alembic migrations and set `DB_INIT_ON_STARTUP=false`.
- React frontend should be maintained as a separate project/workspace and call this API.
- If your tables were created before Alembic setup, run one-time sync:

```bash
alembic stamp head
```
