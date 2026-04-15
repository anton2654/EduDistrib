const RAW_API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

const API_ROOT_URL = RAW_API_BASE_URL.endsWith("/enrollment")
  ? RAW_API_BASE_URL.slice(0, -"/enrollment".length)
  : RAW_API_BASE_URL;

const ENROLLMENT_BASE_URL = `${API_ROOT_URL}/enrollment`;
const AUTH_BASE_URL = `${API_ROOT_URL}/auth`;
const TEACHER_BASE_URL = `${API_ROOT_URL}/teacher`;

let accessToken = null;

export function setAccessToken(token) {
  accessToken = token;
}

export function clearAccessToken() {
  accessToken = null;
}

export function getAccessToken() {
  return accessToken;
}

async function request(baseUrl, path, { method = "GET", body } = {}) {
  const headers = {
    "Content-Type": "application/json",
  };

  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  }

  let response;
  try {
    response = await fetch(`${baseUrl}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new Error(
      "Не вдалося підключитися до API. Перевірте, чи backend запущений і VITE_API_BASE_URL налаштовано правильно.",
    );
  }

  if (!response.ok) {
    let detail = `Request failed: ${response.status}`;

    try {
      const data = await response.json();
      if (typeof data?.detail === "string") {
        detail = data.detail;
      } else if (Array.isArray(data?.detail)) {
        detail = data.detail
          .map((item) => {
            if (typeof item === "string") {
              return item;
            }

            const field = Array.isArray(item?.loc)
              ? item.loc.slice(1).join(".")
              : "";
            const message = item?.msg ?? "Validation error";
            return field ? `${field}: ${message}` : message;
          })
          .join("; ");
      } else if (data?.detail != null) {
        detail = String(data.detail);
      }
    } catch {
      // Keep fallback detail for non-JSON responses.
    }

    if (response.status === 422 && detail.startsWith("Request failed:")) {
      detail = "Некоректні дані форми. Перевірте заповнені поля.";
    }

    throw new Error(detail);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

function toQuery(params) {
  const query = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && `${value}`.trim() !== "") {
      query.set(key, `${value}`);
    }
  });

  const queryString = query.toString();
  return queryString ? `?${queryString}` : "";
}

export async function listCities() {
  return request(ENROLLMENT_BASE_URL, "/cities");
}

export async function listDisciplines() {
  return request(ENROLLMENT_BASE_URL, "/disciplines");
}

export async function listTeachers({ cityId, disciplineId, skip, limit } = {}) {
  return request(
    ENROLLMENT_BASE_URL,
    `/teachers${toQuery({
      city_id: cityId,
      discipline_id: disciplineId,
      skip,
      limit,
    })}`,
  );
}

export async function listStudents({ cityId, email } = {}) {
  return request(
    ENROLLMENT_BASE_URL,
    `/students${toQuery({ city_id: cityId, email })}`,
  );
}

export async function createStudent({ fullName, email, cityId }) {
  return request(ENROLLMENT_BASE_URL, "/students", {
    method: "POST",
    body: {
      full_name: fullName,
      email,
      city_id: Number(cityId),
    },
  });
}

export async function listAvailableSlots({
  cityId,
  disciplineId,
  teacherId,
  skip,
  limit,
} = {}) {
  return request(
    ENROLLMENT_BASE_URL,
    `/slots/available${toQuery({
      city_id: cityId,
      discipline_id: disciplineId,
      teacher_id: teacherId,
      skip,
      limit,
    })}`,
  );
}

export async function getOverviewAnalytics({
  cityId,
  disciplineId,
  teacherId,
  startsFrom,
  endsTo,
} = {}) {
  return request(
    ENROLLMENT_BASE_URL,
    `/analytics/overview${toQuery({
      city_id: cityId,
      discipline_id: disciplineId,
      teacher_id: teacherId,
      starts_from: startsFrom,
      ends_to: endsTo,
    })}`,
  );
}

export async function listTeacherAnalytics({
  cityId,
  disciplineId,
  teacherId,
  startsFrom,
  endsTo,
} = {}) {
  return request(
    ENROLLMENT_BASE_URL,
    `/analytics/teachers${toQuery({
      city_id: cityId,
      discipline_id: disciplineId,
      teacher_id: teacherId,
      starts_from: startsFrom,
      ends_to: endsTo,
    })}`,
  );
}

export async function listDisciplineAnalytics({
  cityId,
  disciplineId,
  teacherId,
  startsFrom,
  endsTo,
} = {}) {
  return request(
    ENROLLMENT_BASE_URL,
    `/analytics/disciplines${toQuery({
      city_id: cityId,
      discipline_id: disciplineId,
      teacher_id: teacherId,
      starts_from: startsFrom,
      ends_to: endsTo,
    })}`,
  );
}

export async function createBooking({ studentId, slotId }) {
  return request(ENROLLMENT_BASE_URL, "/bookings", {
    method: "POST",
    body: {
      student_id: Number(studentId),
      slot_id: Number(slotId),
    },
  });
}

export async function listBookings({ studentId, status, skip, limit } = {}) {
  return request(
    ENROLLMENT_BASE_URL,
    `/bookings${toQuery({ student_id: studentId, status, skip, limit })}`,
  );
}

export async function cancelBooking(bookingId) {
  return request(ENROLLMENT_BASE_URL, `/bookings/${bookingId}`, {
    method: "DELETE",
  });
}

export async function bootstrapAdmin({ username, password }) {
  return request(AUTH_BASE_URL, "/bootstrap-admin", {
    method: "POST",
    body: { username, password },
  });
}

export async function registerStudentAccount({
  username,
  password,
  fullName,
  email,
  cityId,
}) {
  return request(AUTH_BASE_URL, "/register/student", {
    method: "POST",
    body: {
      username,
      password,
      full_name: fullName,
      email,
      city_id: Number(cityId),
    },
  });
}

export async function createTeacherAccount({ username, password, teacherId }) {
  return request(AUTH_BASE_URL, "/register/teacher", {
    method: "POST",
    body: {
      username,
      password,
      teacher_id: Number(teacherId),
    },
  });
}

export async function login({ username, password }) {
  return request(AUTH_BASE_URL, "/login", {
    method: "POST",
    body: { username, password },
  });
}

export async function getCurrentAccount() {
  return request(AUTH_BASE_URL, "/me");
}

export async function listAccounts({ skip, limit } = {}) {
  return request(AUTH_BASE_URL, `/accounts${toQuery({ skip, limit })}`);
}

export async function listTeacherSlots() {
  return request(TEACHER_BASE_URL, "/slots/");
}

export async function listTeacherSlotBookings(
  slotId,
  { status, skip, limit } = {},
) {
  return request(
    TEACHER_BASE_URL,
    `/slots/${slotId}/bookings${toQuery({ status, skip, limit })}`,
  );
}

export async function cancelTeacherSlotBooking(slotId, bookingId) {
  return request(
    TEACHER_BASE_URL,
    `/slots/${slotId}/bookings/${bookingId}/cancel`,
    {
      method: "POST",
    },
  );
}

export async function completeTeacherSlotBooking(slotId, bookingId) {
  return request(
    TEACHER_BASE_URL,
    `/slots/${slotId}/bookings/${bookingId}/complete`,
    {
      method: "POST",
    },
  );
}

export async function createTeacherSlot({
  disciplineId,
  startsAt,
  endsAt,
  capacity,
  isActive,
}) {
  return request(TEACHER_BASE_URL, "/slots/", {
    method: "POST",
    body: {
      discipline_id: Number(disciplineId),
      starts_at: startsAt,
      ends_at: endsAt,
      capacity: Number(capacity),
      is_active: Boolean(isActive),
    },
  });
}

export async function updateTeacherSlot(slotId, payload) {
  const body = {};

  if (payload.disciplineId !== undefined) {
    body.discipline_id = Number(payload.disciplineId);
  }
  if (payload.startsAt !== undefined) {
    body.starts_at = payload.startsAt;
  }
  if (payload.endsAt !== undefined) {
    body.ends_at = payload.endsAt;
  }
  if (payload.capacity !== undefined) {
    body.capacity = Number(payload.capacity);
  }
  if (payload.isActive !== undefined) {
    body.is_active = Boolean(payload.isActive);
  }

  return request(TEACHER_BASE_URL, `/slots/${slotId}`, {
    method: "PUT",
    body,
  });
}

export async function deleteTeacherSlot(slotId) {
  return request(TEACHER_BASE_URL, `/slots/${slotId}`, {
    method: "DELETE",
  });
}
