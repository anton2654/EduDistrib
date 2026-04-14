import { useEffect, useMemo, useState } from "react";
import {
  bootstrapAdmin,
  cancelBooking,
  clearAccessToken,
  createBooking,
  createTeacherAccount,
  createTeacherSlot,
  deleteTeacherSlot,
  getCurrentAccount,
  getAccessToken,
  listAccounts,
  listAvailableSlots,
  listBookings,
  listCities,
  listDisciplines,
  listTeacherSlots,
  listTeachers,
  login,
  registerStudentAccount,
  setAccessToken,
  updateTeacherSlot,
} from "./api/enrollmentApi";
import {
  formatDateTimeRange,
  toDateTimeLocalInputValue,
  toIsoFromLocalInput,
} from "./lib/time";
import "./App.css";

const TOKEN_STORAGE_KEY = "distributor_access_token";

const EMPTY_LOGIN = {
  username: "",
  password: "",
};

const EMPTY_STUDENT_REG = {
  username: "",
  password: "",
  fullName: "",
  email: "",
  cityId: "",
};

const EMPTY_BOOTSTRAP = {
  username: "admin",
  password: "admin12345",
};

const EMPTY_STUDENT_FILTERS = {
  cityId: "",
  disciplineId: "",
  teacherId: "",
};

const EMPTY_TEACHER_SLOT = {
  disciplineId: "",
  startsAt: "",
  endsAt: "",
  capacity: "1",
  isActive: true,
};

const EMPTY_TEACHER_ACCOUNT = {
  username: "",
  password: "",
  teacherId: "",
};

function App() {
  const [cities, setCities] = useState([]);
  const [disciplines, setDisciplines] = useState([]);
  const [teachers, setTeachers] = useState([]);
  const [teacherDirectory, setTeacherDirectory] = useState([]);

  const [studentFilters, setStudentFilters] = useState(EMPTY_STUDENT_FILTERS);
  const [availableSlots, setAvailableSlots] = useState([]);
  const [bookings, setBookings] = useState([]);

  const [teacherSlots, setTeacherSlots] = useState([]);
  const [teacherSlotForm, setTeacherSlotForm] = useState(EMPTY_TEACHER_SLOT);
  const [editingSlotId, setEditingSlotId] = useState(null);
  const [editingSlotForm, setEditingSlotForm] = useState(EMPTY_TEACHER_SLOT);

  const [accounts, setAccounts] = useState([]);
  const [teacherAccountForm, setTeacherAccountForm] = useState(
    EMPTY_TEACHER_ACCOUNT,
  );

  const [currentAccount, setCurrentAccount] = useState(null);

  const [loginDraft, setLoginDraft] = useState(EMPTY_LOGIN);
  const [studentRegisterDraft, setStudentRegisterDraft] =
    useState(EMPTY_STUDENT_REG);
  const [bootstrapDraft, setBootstrapDraft] = useState(EMPTY_BOOTSTRAP);

  const [isCatalogLoading, setIsCatalogLoading] = useState(true);
  const [isSessionLoading, setIsSessionLoading] = useState(false);
  const [isAuthSubmitting, setIsAuthSubmitting] = useState(false);
  const [isSlotsLoading, setIsSlotsLoading] = useState(false);
  const [isBookingsLoading, setIsBookingsLoading] = useState(false);
  const [isTeacherSlotsLoading, setIsTeacherSlotsLoading] = useState(false);
  const [isTeacherSlotSubmitting, setIsTeacherSlotSubmitting] = useState(false);
  const [bookingInProgressSlotId, setBookingInProgressSlotId] = useState(null);
  const [cancelInProgressBookingId, setCancelInProgressBookingId] =
    useState(null);
  const [slotActionInProgressId, setSlotActionInProgressId] = useState(null);
  const [isAdminAccountsLoading, setIsAdminAccountsLoading] = useState(false);

  const [notice, setNotice] = useState({ kind: "info", text: "" });

  const role = currentAccount?.role ?? null;
  const studentId = currentAccount?.student_id ?? null;

  const dashboardStats = useMemo(() => {
    if (!role) {
      return [
        { label: "Міста", value: cities.length },
        { label: "Дисципліни", value: disciplines.length },
        { label: "Викладачі", value: teacherDirectory.length },
      ];
    }

    if (role === "student") {
      return [
        { label: "Вільні слоти", value: availableSlots.length },
        { label: "Мої бронювання", value: bookings.length },
        { label: "Викладачі у фільтрі", value: teachers.length },
      ];
    }

    if (role === "teacher") {
      return [
        { label: "Мої слоти", value: teacherSlots.length },
        {
          label: "Активні слоти",
          value: teacherSlots.filter((slot) => slot.is_active).length,
        },
        {
          label: "Заброньовані місця",
          value: teacherSlots.reduce(
            (sum, slot) => sum + Number(slot.reserved_seats),
            0,
          ),
        },
      ];
    }

    return [
      { label: "Акаунти", value: accounts.length },
      { label: "Викладачі", value: teacherDirectory.length },
      { label: "Міста", value: cities.length },
    ];
  }, [
    accounts.length,
    availableSlots.length,
    bookings.length,
    cities.length,
    disciplines.length,
    role,
    teacherDirectory.length,
    teacherSlots,
    teachers.length,
  ]);

  useEffect(() => {
    async function loadCatalog() {
      setIsCatalogLoading(true);

      try {
        const [loadedCities, loadedDisciplines, loadedTeachers] =
          await Promise.all([listCities(), listDisciplines(), listTeachers()]);

        setCities(loadedCities);
        setDisciplines(loadedDisciplines);
        setTeacherDirectory(loadedTeachers);

        if (loadedCities.length > 0) {
          const defaultCityId = String(loadedCities[0].id);
          setStudentRegisterDraft((previous) => ({
            ...previous,
            cityId: previous.cityId || defaultCityId,
          }));
          setStudentFilters((previous) => ({
            ...previous,
            cityId: previous.cityId || defaultCityId,
          }));
        }

        setTeachers(loadedTeachers);
      } catch (error) {
        setNotice({
          kind: "error",
          text: `Не вдалося завантажити довідники: ${error.message}`,
        });
      } finally {
        setIsCatalogLoading(false);
      }
    }

    void loadCatalog();
  }, []);

  useEffect(() => {
    async function restoreSession() {
      const storedToken = localStorage.getItem(TOKEN_STORAGE_KEY);
      if (!storedToken) {
        return;
      }

      setIsSessionLoading(true);
      setAccessToken(storedToken);

      try {
        const account = await getCurrentAccount();
        setCurrentAccount(account);
      } catch {
        clearAccessToken();
        localStorage.removeItem(TOKEN_STORAGE_KEY);
      } finally {
        setIsSessionLoading(false);
      }
    }

    void restoreSession();
  }, []);

  useEffect(() => {
    if (role !== "student") {
      return;
    }

    async function loadTeachersByFilter() {
      try {
        const loadedTeachers = await listTeachers({
          cityId: studentFilters.cityId || undefined,
          disciplineId: studentFilters.disciplineId || undefined,
        });

        setTeachers(loadedTeachers);

        if (
          studentFilters.teacherId &&
          !loadedTeachers.some(
            (teacher) => teacher.id === Number(studentFilters.teacherId),
          )
        ) {
          setStudentFilters((previous) => ({ ...previous, teacherId: "" }));
        }
      } catch (error) {
        setNotice({
          kind: "error",
          text: `Не вдалося завантажити викладачів: ${error.message}`,
        });
      }
    }

    void loadTeachersByFilter();
  }, [
    role,
    studentFilters.cityId,
    studentFilters.disciplineId,
    studentFilters.teacherId,
  ]);

  useEffect(() => {
    if (role !== "student") {
      setAvailableSlots([]);
      return;
    }

    async function loadSlots() {
      setIsSlotsLoading(true);

      try {
        const slots = await listAvailableSlots({
          cityId: studentFilters.cityId || undefined,
          disciplineId: studentFilters.disciplineId || undefined,
          teacherId: studentFilters.teacherId || undefined,
        });
        setAvailableSlots(slots);
      } catch (error) {
        setNotice({
          kind: "error",
          text: `Не вдалося завантажити слоти: ${error.message}`,
        });
      } finally {
        setIsSlotsLoading(false);
      }
    }

    void loadSlots();
  }, [
    role,
    studentFilters.cityId,
    studentFilters.disciplineId,
    studentFilters.teacherId,
  ]);

  useEffect(() => {
    if (role !== "student" || !studentId) {
      setBookings([]);
      return;
    }

    async function loadBookings() {
      setIsBookingsLoading(true);

      try {
        const loadedBookings = await listBookings();
        setBookings(loadedBookings);
      } catch (error) {
        setNotice({
          kind: "error",
          text: `Не вдалося завантажити бронювання: ${error.message}`,
        });
      } finally {
        setIsBookingsLoading(false);
      }
    }

    void loadBookings();
  }, [role, studentId]);

  useEffect(() => {
    if (role !== "teacher") {
      setTeacherSlots([]);
      return;
    }

    async function loadTeacherSlots() {
      setIsTeacherSlotsLoading(true);

      try {
        const loadedSlots = await listTeacherSlots();
        setTeacherSlots(loadedSlots);
      } catch (error) {
        setNotice({
          kind: "error",
          text: `Не вдалося завантажити слоти викладача: ${error.message}`,
        });
      } finally {
        setIsTeacherSlotsLoading(false);
      }
    }

    void loadTeacherSlots();
  }, [role]);

  useEffect(() => {
    if (role !== "admin") {
      setAccounts([]);
      return;
    }

    async function loadAccounts() {
      setIsAdminAccountsLoading(true);

      try {
        const loadedAccounts = await listAccounts();
        setAccounts(loadedAccounts);
      } catch (error) {
        setNotice({
          kind: "error",
          text: `Не вдалося завантажити акаунти: ${error.message}`,
        });
      } finally {
        setIsAdminAccountsLoading(false);
      }
    }

    void loadAccounts();
  }, [role]);

  function setSessionFromTokenPayload(payload) {
    localStorage.setItem(TOKEN_STORAGE_KEY, payload.access_token);
    setAccessToken(payload.access_token);
    setCurrentAccount({
      user_id: payload.user_id,
      username: payload.username,
      role: payload.role,
      student_id: payload.student_id,
      teacher_id: payload.teacher_id,
      created_at: null,
    });
  }

  async function refreshCurrentAccount() {
    const account = await getCurrentAccount();
    setCurrentAccount(account);
  }

  function handleLogout() {
    clearAccessToken();
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setCurrentAccount(null);
    setBookings([]);
    setTeacherSlots([]);
    setNotice({ kind: "info", text: "Сесію завершено." });
  }

  function handleLoginDraftChange(event) {
    const { name, value } = event.target;
    setLoginDraft((previous) => ({ ...previous, [name]: value }));
  }

  function handleStudentRegisterChange(event) {
    const { name, value } = event.target;
    setStudentRegisterDraft((previous) => ({ ...previous, [name]: value }));
  }

  function handleBootstrapChange(event) {
    const { name, value } = event.target;
    setBootstrapDraft((previous) => ({ ...previous, [name]: value }));
  }

  function handleStudentFilterChange(event) {
    const { name, value } = event.target;
    setStudentFilters((previous) => {
      if (name === "cityId" || name === "disciplineId") {
        return { ...previous, [name]: value, teacherId: "" };
      }
      return { ...previous, [name]: value };
    });
  }

  function handleTeacherSlotFormChange(event) {
    const { name, value, type, checked } = event.target;
    setTeacherSlotForm((previous) => ({
      ...previous,
      [name]: type === "checkbox" ? checked : value,
    }));
  }

  function handleEditSlotFormChange(event) {
    const { name, value, type, checked } = event.target;
    setEditingSlotForm((previous) => ({
      ...previous,
      [name]: type === "checkbox" ? checked : value,
    }));
  }

  function handleTeacherAccountChange(event) {
    const { name, value } = event.target;
    setTeacherAccountForm((previous) => ({ ...previous, [name]: value }));
  }

  async function handleLogin(event) {
    event.preventDefault();
    setIsAuthSubmitting(true);

    try {
      const payload = await login({
        username: loginDraft.username.trim().toLowerCase(),
        password: loginDraft.password,
      });
      setSessionFromTokenPayload(payload);
      await refreshCurrentAccount();
      setLoginDraft(EMPTY_LOGIN);
      setNotice({ kind: "success", text: "Вхід виконано успішно." });
    } catch (error) {
      setNotice({ kind: "error", text: `Помилка входу: ${error.message}` });
    } finally {
      setIsAuthSubmitting(false);
    }
  }

  async function handleStudentRegister(event) {
    event.preventDefault();
    setIsAuthSubmitting(true);

    try {
      const payload = await registerStudentAccount({
        username: studentRegisterDraft.username.trim().toLowerCase(),
        password: studentRegisterDraft.password,
        fullName: studentRegisterDraft.fullName.trim(),
        email: studentRegisterDraft.email.trim().toLowerCase(),
        cityId: studentRegisterDraft.cityId,
      });
      setSessionFromTokenPayload(payload);
      await refreshCurrentAccount();
      setStudentRegisterDraft((previous) => ({
        ...EMPTY_STUDENT_REG,
        cityId: previous.cityId,
      }));
      setNotice({
        kind: "success",
        text: "Студентський акаунт створено і авторизовано.",
      });
    } catch (error) {
      setNotice({
        kind: "error",
        text: `Не вдалося зареєструвати студента: ${error.message}`,
      });
    } finally {
      setIsAuthSubmitting(false);
    }
  }

  async function handleBootstrapAdmin(event) {
    event.preventDefault();
    setIsAuthSubmitting(true);

    try {
      const payload = await bootstrapAdmin({
        username: bootstrapDraft.username.trim().toLowerCase(),
        password: bootstrapDraft.password,
      });
      setSessionFromTokenPayload(payload);
      await refreshCurrentAccount();
      setNotice({
        kind: "success",
        text: "Admin bootstrap виконано. Тепер можна створювати teacher-акаунти.",
      });
    } catch (error) {
      setNotice({
        kind: "warning",
        text: `Bootstrap не виконано: ${error.message}`,
      });
    } finally {
      setIsAuthSubmitting(false);
    }
  }

  async function handleBookSlot(slotId) {
    if (!studentId) {
      setNotice({
        kind: "warning",
        text: "Student profile не привʼязаний до акаунта.",
      });
      return;
    }

    setBookingInProgressSlotId(slotId);

    try {
      await createBooking({ studentId, slotId });

      const [slots, loadedBookings] = await Promise.all([
        listAvailableSlots({
          cityId: studentFilters.cityId || undefined,
          disciplineId: studentFilters.disciplineId || undefined,
          teacherId: studentFilters.teacherId || undefined,
        }),
        listBookings(),
      ]);

      setAvailableSlots(slots);
      setBookings(loadedBookings);
      setNotice({ kind: "success", text: "Бронювання створено." });
    } catch (error) {
      setNotice({
        kind: "error",
        text: `Бронювання не створено: ${error.message}`,
      });
    } finally {
      setBookingInProgressSlotId(null);
    }
  }

  async function handleCancelBooking(bookingId) {
    setCancelInProgressBookingId(bookingId);

    try {
      await cancelBooking(bookingId);

      const [slots, loadedBookings] = await Promise.all([
        listAvailableSlots({
          cityId: studentFilters.cityId || undefined,
          disciplineId: studentFilters.disciplineId || undefined,
          teacherId: studentFilters.teacherId || undefined,
        }),
        listBookings(),
      ]);

      setAvailableSlots(slots);
      setBookings(loadedBookings);
      setNotice({ kind: "success", text: "Бронювання скасовано." });
    } catch (error) {
      setNotice({
        kind: "error",
        text: `Не вдалося скасувати: ${error.message}`,
      });
    } finally {
      setCancelInProgressBookingId(null);
    }
  }

  async function handleCreateTeacherSlot(event) {
    event.preventDefault();
    setIsTeacherSlotSubmitting(true);

    try {
      await createTeacherSlot({
        disciplineId: teacherSlotForm.disciplineId,
        startsAt: toIsoFromLocalInput(teacherSlotForm.startsAt),
        endsAt: toIsoFromLocalInput(teacherSlotForm.endsAt),
        capacity: teacherSlotForm.capacity,
        isActive: teacherSlotForm.isActive,
      });

      const loadedSlots = await listTeacherSlots();
      setTeacherSlots(loadedSlots);
      setTeacherSlotForm(EMPTY_TEACHER_SLOT);
      setNotice({ kind: "success", text: "Слот викладача створено." });
    } catch (error) {
      setNotice({
        kind: "error",
        text: `Не вдалося створити слот: ${error.message}`,
      });
    } finally {
      setIsTeacherSlotSubmitting(false);
    }
  }

  function startEditingSlot(slot) {
    setEditingSlotId(slot.slot_id);
    setEditingSlotForm({
      disciplineId: String(slot.discipline_id),
      startsAt: toDateTimeLocalInputValue(slot.starts_at),
      endsAt: toDateTimeLocalInputValue(slot.ends_at),
      capacity: String(slot.capacity),
      isActive: Boolean(slot.is_active),
    });
  }

  async function handleUpdateTeacherSlot(event) {
    event.preventDefault();

    if (!editingSlotId) {
      return;
    }

    setSlotActionInProgressId(editingSlotId);

    try {
      await updateTeacherSlot(editingSlotId, {
        disciplineId: editingSlotForm.disciplineId,
        startsAt: toIsoFromLocalInput(editingSlotForm.startsAt),
        endsAt: toIsoFromLocalInput(editingSlotForm.endsAt),
        capacity: editingSlotForm.capacity,
        isActive: editingSlotForm.isActive,
      });

      const loadedSlots = await listTeacherSlots();
      setTeacherSlots(loadedSlots);
      setEditingSlotId(null);
      setEditingSlotForm(EMPTY_TEACHER_SLOT);
      setNotice({ kind: "success", text: "Слот оновлено." });
    } catch (error) {
      setNotice({
        kind: "error",
        text: `Не вдалося оновити слот: ${error.message}`,
      });
    } finally {
      setSlotActionInProgressId(null);
    }
  }

  async function handleDeleteTeacherSlot(slotId) {
    setSlotActionInProgressId(slotId);

    try {
      await deleteTeacherSlot(slotId);
      const loadedSlots = await listTeacherSlots();
      setTeacherSlots(loadedSlots);
      if (editingSlotId === slotId) {
        setEditingSlotId(null);
      }
      setNotice({ kind: "success", text: "Слот видалено." });
    } catch (error) {
      setNotice({
        kind: "error",
        text: `Не вдалося видалити слот: ${error.message}`,
      });
    } finally {
      setSlotActionInProgressId(null);
    }
  }

  async function handleToggleTeacherSlotActive(slot) {
    setSlotActionInProgressId(slot.slot_id);

    try {
      await updateTeacherSlot(slot.slot_id, { isActive: !slot.is_active });
      const loadedSlots = await listTeacherSlots();
      setTeacherSlots(loadedSlots);
      setNotice({
        kind: "success",
        text: slot.is_active ? "Слот деактивовано." : "Слот активовано.",
      });
    } catch (error) {
      setNotice({
        kind: "error",
        text: `Не вдалося змінити активність: ${error.message}`,
      });
    } finally {
      setSlotActionInProgressId(null);
    }
  }

  async function handleCreateTeacherAccount(event) {
    event.preventDefault();
    setIsAdminAccountsLoading(true);

    try {
      await createTeacherAccount({
        username: teacherAccountForm.username.trim().toLowerCase(),
        password: teacherAccountForm.password,
        teacherId: teacherAccountForm.teacherId,
      });

      const loadedAccounts = await listAccounts();
      setAccounts(loadedAccounts);
      setTeacherAccountForm(EMPTY_TEACHER_ACCOUNT);
      setNotice({ kind: "success", text: "Teacher account створено." });
    } catch (error) {
      setNotice({
        kind: "error",
        text: `Не вдалося створити teacher account: ${error.message}`,
      });
    } finally {
      setIsAdminAccountsLoading(false);
    }
  }

  const authTokenPresent = Boolean(getAccessToken());

  return (
    <div className="page-shell">
      <header className="hero-panel reveal">
        <p className="eyebrow">Role-Based Academic Distribution</p>
        <h1>Керуйте записами студентів за ролями</h1>
        <p className="hero-copy">
          Student бронює, Teacher керує слотами, Admin контролює доступи. Усе
          працює через один API та прозору рольову авторизацію.
        </p>

        <div className="stats-grid">
          {dashboardStats.map((metric, index) => (
            <article
              className="stat-card"
              key={metric.label}
              style={{ animationDelay: `${index * 90 + 120}ms` }}
            >
              <p className="stat-value">{metric.value}</p>
              <p className="stat-label">{metric.label}</p>
            </article>
          ))}
        </div>
      </header>

      {notice.text && (
        <div className={`notice ${notice.kind}`}>{notice.text}</div>
      )}

      {currentAccount ? (
        <section
          className="panel reveal top-nav"
          style={{ animationDelay: "120ms" }}
        >
          <div>
            <p className="meta-line">
              Увійшли як <strong>{currentAccount.username}</strong>
            </p>
            <p className="meta-line role-line">Роль: {currentAccount.role}</p>
          </div>

          <button type="button" className="ghost" onClick={handleLogout}>
            Вийти
          </button>
        </section>
      ) : null}

      {!currentAccount ? (
        <section className="auth-grid">
          <article className="panel reveal" style={{ animationDelay: "180ms" }}>
            <h2>Вхід у систему</h2>
            <form className="profile-form" onSubmit={handleLogin}>
              <label>
                Username
                <input
                  name="username"
                  value={loginDraft.username}
                  onChange={handleLoginDraftChange}
                  placeholder="teacher_ivan"
                  autoComplete="username"
                />
              </label>
              <label>
                Password
                <input
                  name="password"
                  type="password"
                  value={loginDraft.password}
                  onChange={handleLoginDraftChange}
                  placeholder="teacher123"
                  autoComplete="current-password"
                />
              </label>
              <button
                type="submit"
                disabled={isAuthSubmitting || isSessionLoading}
              >
                Увійти
              </button>
            </form>

            <p className="hint-text">
              Demo: admin/admin12345, teacher_ivan/teacher123,
              student_andriy/student123
            </p>
          </article>

          <article className="panel reveal" style={{ animationDelay: "260ms" }}>
            <h2>Реєстрація студента</h2>
            <form className="profile-form" onSubmit={handleStudentRegister}>
              <label>
                Username
                <input
                  name="username"
                  value={studentRegisterDraft.username}
                  onChange={handleStudentRegisterChange}
                  placeholder="new_student"
                />
              </label>

              <label>
                Password
                <input
                  name="password"
                  type="password"
                  value={studentRegisterDraft.password}
                  onChange={handleStudentRegisterChange}
                  placeholder="Не менше 6 символів"
                />
              </label>

              <label>
                Повне імʼя
                <input
                  name="fullName"
                  value={studentRegisterDraft.fullName}
                  onChange={handleStudentRegisterChange}
                  placeholder="Андрій Мельник"
                />
              </label>

              <label>
                Email
                <input
                  name="email"
                  type="email"
                  value={studentRegisterDraft.email}
                  onChange={handleStudentRegisterChange}
                  placeholder="student@example.com"
                />
              </label>

              <label>
                Місто
                <select
                  name="cityId"
                  value={studentRegisterDraft.cityId}
                  onChange={handleStudentRegisterChange}
                  disabled={isCatalogLoading}
                >
                  <option value="">Оберіть місто</option>
                  {cities.map((city) => (
                    <option key={city.id} value={city.id}>
                      {city.name}
                    </option>
                  ))}
                </select>
              </label>

              <button
                type="submit"
                disabled={isAuthSubmitting || isCatalogLoading}
              >
                Зареєструватися як Student
              </button>
            </form>
          </article>

          <article className="panel reveal" style={{ animationDelay: "340ms" }}>
            <h2>Bootstrap Admin (одноразово)</h2>
            <form className="profile-form" onSubmit={handleBootstrapAdmin}>
              <label>
                Admin username
                <input
                  name="username"
                  value={bootstrapDraft.username}
                  onChange={handleBootstrapChange}
                />
              </label>
              <label>
                Admin password
                <input
                  name="password"
                  type="password"
                  value={bootstrapDraft.password}
                  onChange={handleBootstrapChange}
                />
              </label>
              <button type="submit" disabled={isAuthSubmitting}>
                Ініціалізувати Admin
              </button>
            </form>
          </article>
        </section>
      ) : null}

      {currentAccount?.role === "student" ? (
        <>
          <section className="two-column">
            <article
              className="panel reveal"
              style={{ animationDelay: "200ms" }}
            >
              <h2>Фільтри слотів</h2>

              <div className="filters-grid">
                <label>
                  Місто
                  <select
                    name="cityId"
                    value={studentFilters.cityId}
                    onChange={handleStudentFilterChange}
                  >
                    <option value="">Усі міста</option>
                    {cities.map((city) => (
                      <option key={city.id} value={city.id}>
                        {city.name}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  Дисципліна
                  <select
                    name="disciplineId"
                    value={studentFilters.disciplineId}
                    onChange={handleStudentFilterChange}
                  >
                    <option value="">Усі дисципліни</option>
                    {disciplines.map((discipline) => (
                      <option key={discipline.id} value={discipline.id}>
                        {discipline.name}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  Викладач
                  <select
                    name="teacherId"
                    value={studentFilters.teacherId}
                    onChange={handleStudentFilterChange}
                  >
                    <option value="">Усі викладачі</option>
                    {teachers.map((teacher) => (
                      <option key={teacher.id} value={teacher.id}>
                        {teacher.full_name}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            </article>

            <article
              className="panel reveal"
              style={{ animationDelay: "260ms" }}
            >
              <h2>Student Session</h2>
              <p className="meta-line">
                Token активний: {authTokenPresent ? "так" : "ні"}
              </p>
              <p className="meta-line">
                Student ID: {studentId ?? "не прив'язано"}
              </p>
              <p className="hint-text">
                У ролі Student API автоматично обмежує доступ тільки до власних
                бронювань.
              </p>
            </article>
          </section>

          <section className="panel reveal" style={{ animationDelay: "320ms" }}>
            <div className="panel-header-row">
              <h2>Вільні слоти</h2>
              <span className="badge">
                {isSlotsLoading
                  ? "Оновлення..."
                  : `Знайдено: ${availableSlots.length}`}
              </span>
            </div>

            {availableSlots.length === 0 && !isSlotsLoading ? (
              <p className="empty-state">
                Слоти за поточними фільтрами відсутні.
              </p>
            ) : (
              <div className="slot-grid">
                {availableSlots.map((slot, index) => (
                  <article
                    className="slot-card"
                    key={slot.slot_id}
                    style={{ animationDelay: `${index * 70 + 180}ms` }}
                  >
                    <p className="slot-topic">{slot.discipline_name}</p>
                    <h3>{slot.teacher_name}</h3>
                    <p className="slot-meta">{slot.city_name}</p>
                    <p className="slot-time">
                      {formatDateTimeRange(slot.starts_at, slot.ends_at)}
                    </p>
                    <p className="slot-capacity">
                      Місця: {slot.available_seats}/{slot.capacity}
                    </p>

                    <button
                      type="button"
                      onClick={() => void handleBookSlot(slot.slot_id)}
                      disabled={
                        bookingInProgressSlotId === slot.slot_id ||
                        slot.available_seats <= 0
                      }
                    >
                      {bookingInProgressSlotId === slot.slot_id
                        ? "Бронюю..."
                        : "Записатися"}
                    </button>
                  </article>
                ))}
              </div>
            )}
          </section>

          <section className="panel reveal" style={{ animationDelay: "420ms" }}>
            <div className="panel-header-row">
              <h2>Мої бронювання</h2>
              <span className="badge">
                {isBookingsLoading
                  ? "Оновлення..."
                  : `У списку: ${bookings.length}`}
              </span>
            </div>

            {bookings.length === 0 && !isBookingsLoading ? (
              <p className="empty-state">Поки що немає активних бронювань.</p>
            ) : (
              <div className="booking-list">
                {bookings.map((booking, index) => (
                  <article
                    className="booking-item"
                    key={booking.booking_id}
                    style={{ animationDelay: `${index * 70 + 220}ms` }}
                  >
                    <div>
                      <p className="slot-topic">{booking.discipline_name}</p>
                      <h3>{booking.teacher_name}</h3>
                      <p className="slot-meta">{booking.city_name}</p>
                      <p className="slot-time">
                        {formatDateTimeRange(
                          booking.starts_at,
                          booking.ends_at,
                        )}
                      </p>
                    </div>

                    <button
                      type="button"
                      className="ghost"
                      onClick={() =>
                        void handleCancelBooking(booking.booking_id)
                      }
                      disabled={
                        cancelInProgressBookingId === booking.booking_id
                      }
                    >
                      {cancelInProgressBookingId === booking.booking_id
                        ? "Скасовую..."
                        : "Скасувати"}
                    </button>
                  </article>
                ))}
              </div>
            )}
          </section>
        </>
      ) : null}

      {currentAccount?.role === "teacher" ? (
        <>
          <section className="panel reveal" style={{ animationDelay: "240ms" }}>
            <h2>Створити новий слот</h2>

            <form className="slot-form-grid" onSubmit={handleCreateTeacherSlot}>
              <label>
                Дисципліна
                <select
                  name="disciplineId"
                  value={teacherSlotForm.disciplineId}
                  onChange={handleTeacherSlotFormChange}
                  required
                >
                  <option value="">Оберіть дисципліну</option>
                  {disciplines.map((discipline) => (
                    <option key={discipline.id} value={discipline.id}>
                      {discipline.name}
                    </option>
                  ))}
                </select>
              </label>

              <label>
                Початок
                <input
                  name="startsAt"
                  type="datetime-local"
                  value={teacherSlotForm.startsAt}
                  onChange={handleTeacherSlotFormChange}
                  required
                />
              </label>

              <label>
                Завершення
                <input
                  name="endsAt"
                  type="datetime-local"
                  value={teacherSlotForm.endsAt}
                  onChange={handleTeacherSlotFormChange}
                  required
                />
              </label>

              <label>
                Місткість
                <input
                  name="capacity"
                  type="number"
                  min="1"
                  value={teacherSlotForm.capacity}
                  onChange={handleTeacherSlotFormChange}
                  required
                />
              </label>

              <label className="checkbox-row">
                <input
                  name="isActive"
                  type="checkbox"
                  checked={teacherSlotForm.isActive}
                  onChange={handleTeacherSlotFormChange}
                />
                Активний одразу
              </label>

              <button type="submit" disabled={isTeacherSlotSubmitting}>
                {isTeacherSlotSubmitting ? "Створюю..." : "Створити слот"}
              </button>
            </form>
          </section>

          <section className="panel reveal" style={{ animationDelay: "320ms" }}>
            <div className="panel-header-row">
              <h2>Керування моїми слотами</h2>
              <span className="badge">
                {isTeacherSlotsLoading
                  ? "Оновлення..."
                  : `Слотів: ${teacherSlots.length}`}
              </span>
            </div>

            {teacherSlots.length === 0 && !isTeacherSlotsLoading ? (
              <p className="empty-state">Поки що немає створених слотів.</p>
            ) : (
              <div className="teacher-slot-grid">
                {teacherSlots.map((slot, index) => (
                  <article
                    key={slot.slot_id}
                    className="slot-card"
                    style={{ animationDelay: `${index * 70 + 180}ms` }}
                  >
                    <p className="slot-topic">{slot.discipline_name}</p>
                    <h3>{formatDateTimeRange(slot.starts_at, slot.ends_at)}</h3>
                    <p className="slot-meta">
                      Місць: {slot.available_seats}/{slot.capacity} ·
                      Заброньовано: {slot.reserved_seats}
                    </p>
                    <p className="slot-meta">
                      Статус: {slot.is_active ? "Активний" : "Неактивний"}
                    </p>

                    <div className="inline-actions">
                      <button
                        type="button"
                        className="ghost"
                        onClick={() => startEditingSlot(slot)}
                      >
                        Редагувати
                      </button>
                      <button
                        type="button"
                        className="ghost"
                        onClick={() => void handleToggleTeacherSlotActive(slot)}
                        disabled={slotActionInProgressId === slot.slot_id}
                      >
                        {slot.is_active ? "Деактивувати" : "Активувати"}
                      </button>
                      <button
                        type="button"
                        className="danger"
                        onClick={() =>
                          void handleDeleteTeacherSlot(slot.slot_id)
                        }
                        disabled={slotActionInProgressId === slot.slot_id}
                      >
                        Видалити
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>

          {editingSlotId ? (
            <section
              className="panel reveal"
              style={{ animationDelay: "380ms" }}
            >
              <h2>Редагування слота #{editingSlotId}</h2>
              <form
                className="slot-form-grid"
                onSubmit={handleUpdateTeacherSlot}
              >
                <label>
                  Дисципліна
                  <select
                    name="disciplineId"
                    value={editingSlotForm.disciplineId}
                    onChange={handleEditSlotFormChange}
                    required
                  >
                    <option value="">Оберіть дисципліну</option>
                    {disciplines.map((discipline) => (
                      <option key={discipline.id} value={discipline.id}>
                        {discipline.name}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  Початок
                  <input
                    name="startsAt"
                    type="datetime-local"
                    value={editingSlotForm.startsAt}
                    onChange={handleEditSlotFormChange}
                    required
                  />
                </label>

                <label>
                  Завершення
                  <input
                    name="endsAt"
                    type="datetime-local"
                    value={editingSlotForm.endsAt}
                    onChange={handleEditSlotFormChange}
                    required
                  />
                </label>

                <label>
                  Місткість
                  <input
                    name="capacity"
                    type="number"
                    min="1"
                    value={editingSlotForm.capacity}
                    onChange={handleEditSlotFormChange}
                    required
                  />
                </label>

                <label className="checkbox-row">
                  <input
                    name="isActive"
                    type="checkbox"
                    checked={editingSlotForm.isActive}
                    onChange={handleEditSlotFormChange}
                  />
                  Активний
                </label>

                <div className="inline-actions">
                  <button
                    type="submit"
                    disabled={slotActionInProgressId === editingSlotId}
                  >
                    Зберегти зміни
                  </button>
                  <button
                    type="button"
                    className="ghost"
                    onClick={() => setEditingSlotId(null)}
                  >
                    Скасувати
                  </button>
                </div>
              </form>
            </section>
          ) : null}
        </>
      ) : null}

      {currentAccount?.role === "admin" ? (
        <section className="two-column">
          <article className="panel reveal" style={{ animationDelay: "220ms" }}>
            <h2>Створення Teacher Account</h2>
            <form
              className="profile-form"
              onSubmit={handleCreateTeacherAccount}
            >
              <label>
                Username
                <input
                  name="username"
                  value={teacherAccountForm.username}
                  onChange={handleTeacherAccountChange}
                  placeholder="teacher_new"
                />
              </label>

              <label>
                Password
                <input
                  name="password"
                  type="password"
                  value={teacherAccountForm.password}
                  onChange={handleTeacherAccountChange}
                  placeholder="Не менше 6 символів"
                />
              </label>

              <label>
                Teacher profile
                <select
                  name="teacherId"
                  value={teacherAccountForm.teacherId}
                  onChange={handleTeacherAccountChange}
                >
                  <option value="">Оберіть викладача</option>
                  {teacherDirectory.map((teacher) => (
                    <option key={teacher.id} value={teacher.id}>
                      {teacher.full_name}
                    </option>
                  ))}
                </select>
              </label>

              <button type="submit" disabled={isAdminAccountsLoading}>
                Створити teacher account
              </button>
            </form>
          </article>

          <article className="panel reveal" style={{ animationDelay: "300ms" }}>
            <div className="panel-header-row">
              <h2>Усі акаунти</h2>
              <span className="badge">
                {isAdminAccountsLoading
                  ? "Оновлення..."
                  : `Кількість: ${accounts.length}`}
              </span>
            </div>

            <div className="account-list">
              {accounts.map((account) => (
                <div className="account-item" key={account.user_id}>
                  <p>
                    <strong>{account.username}</strong> · {account.role}
                  </p>
                  <p className="meta-line">
                    student_id: {account.student_id ?? "-"}, teacher_id:{" "}
                    {account.teacher_id ?? "-"}
                  </p>
                </div>
              ))}
            </div>
          </article>
        </section>
      ) : null}
    </div>
  );
}

export default App;
