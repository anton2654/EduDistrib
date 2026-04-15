from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_booking_lifecycle_create_list_cancel() -> None:
    suffix = uuid4().hex[:8]

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        cities_response = await client.get("/api/v1/enrollment/cities")
        assert cities_response.status_code == 200
        cities = cities_response.json()
        if not cities:
            pytest.skip("No cities available. Seed demo data before running this test.")

        city_id = cities[0]["id"]

        register_response = await client.post(
            "/api/v1/auth/register/student",
            json={
                "username": f"student_{suffix}",
                "password": "student123",
                "full_name": f"Student {suffix}",
                "email": f"student-{suffix}@example.com",
                "city_id": city_id,
            },
        )
        assert register_response.status_code == 201
        auth_payload = register_response.json()
        student_id = auth_payload["student_id"]
        assert student_id is not None

        slots_response = await client.get("/api/v1/enrollment/slots/available")
        assert slots_response.status_code == 200
        slots = slots_response.json()
        if not slots:
            pytest.skip("No available slots found. Seed demo data before running this test.")

        slot_id = slots[0]["slot_id"]
        auth_headers = {"Authorization": f"Bearer {auth_payload['access_token']}"}

        create_booking_response = await client.post(
            "/api/v1/enrollment/bookings",
            json={"student_id": student_id, "slot_id": slot_id},
            headers=auth_headers,
        )
        assert create_booking_response.status_code == 201
        created_booking_payload = create_booking_response.json()
        booking_id = created_booking_payload["id"]
        assert created_booking_payload["status"] == "active"

        list_booking_response = await client.get(
            "/api/v1/enrollment/bookings",
            headers=auth_headers,
        )
        assert list_booking_response.status_code == 200
        bookings = list_booking_response.json()
        booked_ids = [booking["booking_id"] for booking in bookings]
        assert booking_id in booked_ids
        created_booking = next(booking for booking in bookings if booking["booking_id"] == booking_id)
        assert created_booking["student_id"] == student_id
        assert created_booking["slot_id"] == slot_id

        cancel_response = await client.delete(
            f"/api/v1/enrollment/bookings/{booking_id}",
            headers=auth_headers,
        )
        assert cancel_response.status_code == 204

        list_after_cancel_response = await client.get(
            "/api/v1/enrollment/bookings",
            headers=auth_headers,
        )
        assert list_after_cancel_response.status_code == 200
        cancelled_booking = next(
            booking
            for booking in list_after_cancel_response.json()
            if booking["booking_id"] == booking_id
        )
        assert cancelled_booking["status"] == "cancelled"

        active_only_response = await client.get(
            "/api/v1/enrollment/bookings?status=active",
            headers=auth_headers,
        )
        assert active_only_response.status_code == 200
        active_ids = {booking["booking_id"] for booking in active_only_response.json()}
        assert booking_id not in active_ids
