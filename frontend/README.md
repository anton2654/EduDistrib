# Distributor Frontend

React + Vite client for student-teacher enrollment workflow.

Roles in UI:

- Student dashboard (discover slots, create/cancel bookings)
- Teacher dashboard (manage own slots)
- Admin panel (create teacher accounts)
- Admin analytics (overview KPIs + teacher/discipline performance filters)

## Setup

1. Copy `.env.example` to `.env`.
2. Ensure backend API is running on configured URL.
3. Install dependencies:

```bash
npm install
```

## Run

```bash
npm run dev
```

Default frontend URL: `http://localhost:5173`

## Build and lint

```bash
npm run lint
npm run build
```

## Environment

- `VITE_API_BASE_URL` - base URL for backend API root. Default:

```text
http://127.0.0.1:8000/api/v1
```
