import { useEffect, useMemo, useRef, useState } from "react";
import {
  cancelTeacherSlotBooking,
  cancelBooking,
  clearAccessToken,
  completeTeacherSlotBooking,
  createReview,
  createBooking,
  createTeacherAccount,
  createTeacherSlot,
  deleteTeacherSlot,
  getCurrentAccount,
  getOverviewAnalytics,
  getAccessToken,
  listAccounts,
  listAvailableSlots,
  listBookings,
  listCities,
  listDisciplineAnalytics,
  listDisciplines,
  listTeacherSlotBookings,
  listTeacherAnalytics,
  listTeacherSlots,
  listTeachers,
  login,
  registerStudentAccount,
  setAccessToken,
  updateCurrentAccount,
  updateTeacherSlot,
} from "./api/enrollmentApi";
import {
  formatDateTimeRange,
  toDateTimeLocalInputValue,
  toIsoFromLocalInput,
} from "./lib/time";
import "./App.css";

const TOKEN_STORAGE_KEY = "distributor_access_token";
const ADMIN_ACCOUNTS_PAGE_SIZE = 5;

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

const EMPTY_STUDENT_FILTERS = {
  cityId: "",
  disciplineId: "",
  teacherSearch: "",
  teacherId: "",
};

const EMPTY_PROFILE_UPDATE_DRAFT = {
  cityId: "",
  currentPassword: "",
  newPassword: "",
};

const EMPTY_REVIEW_DRAFT = {
  rating: "5",
  comment: "",
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

const EMPTY_ADMIN_ANALYTICS_FILTERS = {
  cityId: "",
  disciplineId: "",
  teacherId: "",
  startsFrom: "",
  endsTo: "",
};

function App() {
  const userMenuWrapRef = useRef(null);

  const [currentPath, setCurrentPath] = useState(() =>
    typeof window !== "undefined" ? window.location.pathname || "/" : "/",
  );
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [profileFocusSection, setProfileFocusSection] = useState("profile");

  const [cities, setCities] = useState([]);
  const [disciplines, setDisciplines] = useState([]);
  const [teachers, setTeachers] = useState([]);
  const [teacherDirectory, setTeacherDirectory] = useState([]);

  const [studentFilters, setStudentFilters] = useState(EMPTY_STUDENT_FILTERS);
  const [availableSlots, setAvailableSlots] = useState([]);
  const [bookings, setBookings] = useState([]);

  const [teacherSlots, setTeacherSlots] = useState([]);
  const [teacherSlotBookingsBySlotId, setTeacherSlotBookingsBySlotId] =
    useState({});
  const [expandedTeacherSlotId, setExpandedTeacherSlotId] = useState(null);
  const [teacherBookingsLoadingSlotId, setTeacherBookingsLoadingSlotId] =
    useState(null);
  const [teacherBookingActionKey, setTeacherBookingActionKey] = useState(null);
  const [teacherSlotForm, setTeacherSlotForm] = useState(EMPTY_TEACHER_SLOT);
  const [editingSlotId, setEditingSlotId] = useState(null);
  const [editingSlotForm, setEditingSlotForm] = useState(EMPTY_TEACHER_SLOT);

  const [accounts, setAccounts] = useState([]);
  const [teacherAccountForm, setTeacherAccountForm] = useState(
    EMPTY_TEACHER_ACCOUNT,
  );
  const [adminAnalyticsFilters, setAdminAnalyticsFilters] = useState(
    EMPTY_ADMIN_ANALYTICS_FILTERS,
  );
  const [overviewAnalytics, setOverviewAnalytics] = useState(null);
  const [teacherAnalyticsRows, setTeacherAnalyticsRows] = useState([]);
  const [disciplineAnalyticsRows, setDisciplineAnalyticsRows] = useState([]);
  const [adminAccountsSkip, setAdminAccountsSkip] = useState(0);
  const [hasMoreAdminAccounts, setHasMoreAdminAccounts] = useState(false);
  const [profileUpdateDraft, setProfileUpdateDraft] = useState(
    EMPTY_PROFILE_UPDATE_DRAFT,
  );

  const [studentBookingTab, setStudentBookingTab] = useState("upcoming");
  const [reviewEditorBookingId, setReviewEditorBookingId] = useState(null);
  const [reviewDraftByBookingId, setReviewDraftByBookingId] = useState({});

  const [currentAccount, setCurrentAccount] = useState(null);

  const [loginDraft, setLoginDraft] = useState(EMPTY_LOGIN);
  const [studentRegisterDraft, setStudentRegisterDraft] =
    useState(EMPTY_STUDENT_REG);

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
  const [isAdminAnalyticsLoading, setIsAdminAnalyticsLoading] = useState(false);
  const [isProfileSubmitting, setIsProfileSubmitting] = useState(false);
  const [reviewSubmittingBookingId, setReviewSubmittingBookingId] =
    useState(null);

  const [notice, setNotice] = useState({ kind: "info", text: "" });

  const role = currentAccount?.role ?? null;
  const studentId = currentAccount?.student_id ?? null;
  const isProfilePage = currentPath === "/profile";
  const canEditProfileCity = role === "student" || role === "teacher";

  const activeStudentBookingSlotIds = useMemo(
    () =>
      new Set(
        bookings
          .filter((booking) => (booking.status ?? "active") === "active")
          .map((booking) => booking.slot_id),
      ),
    [bookings],
  );

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
      {
        label: "Слоти у вибірці",
        value: overviewAnalytics?.filtered_slots_total ?? 0,
      },
      {
        label: "Завантаження, %",
        value: overviewAnalytics?.utilization_rate_percent ?? 0,
      },
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
    overviewAnalytics,
  ]);

  const upcomingBookings = useMemo(
    () =>
      bookings.filter((booking) => (booking.status ?? "active") === "active"),
    [bookings],
  );
  const historyBookings = useMemo(
    () =>
      bookings.filter((booking) => (booking.status ?? "active") !== "active"),
    [bookings],
  );
  const shownBookings =
    studentBookingTab === "upcoming" ? upcomingBookings : historyBookings;

  const userDisplayName =
    currentAccount?.full_name || currentAccount?.username || "U";
  const userInitials = useMemo(() => {
    const parts = userDisplayName
      .split(" ")
      .map((part) => part.trim())
      .filter(Boolean);

    if (parts.length === 0) {
      return "U";
    }
    if (parts.length === 1) {
      return parts[0].slice(0, 2).toUpperCase();
    }
    return `${parts[0][0] ?? ""}${parts[1][0] ?? ""}`.toUpperCase();
  }, [userDisplayName]);

  const expandedTeacherSlot = useMemo(
    () =>
      expandedTeacherSlotId != null
        ? teacherSlots.find((slot) => slot.slot_id === expandedTeacherSlotId) ||
          null
        : null,
    [expandedTeacherSlotId, teacherSlots],
  );

  const expandedTeacherSlotBookings = useMemo(
    () =>
      expandedTeacherSlotId != null
        ? (teacherSlotBookingsBySlotId[expandedTeacherSlotId] ?? [])
        : [],
    [expandedTeacherSlotId, teacherSlotBookingsBySlotId],
  );

  const teacherRatingById = useMemo(
    () =>
      new Map(
        teachers
          .filter((teacher) => teacher.average_rating != null)
          .map((teacher) => [teacher.id, teacher.average_rating]),
      ),
    [teachers],
  );

  async function loadAdminAccountsPage(skipValue) {
    const loadedAccounts = await listAccounts({
      skip: skipValue,
      limit: ADMIN_ACCOUNTS_PAGE_SIZE + 1,
    });

    setHasMoreAdminAccounts(loadedAccounts.length > ADMIN_ACCOUNTS_PAGE_SIZE);
    setAccounts(loadedAccounts.slice(0, ADMIN_ACCOUNTS_PAGE_SIZE));
  }

  function navigateTo(path, focusSection = "profile") {
    if (typeof window !== "undefined" && window.location.pathname !== path) {
      window.history.pushState({}, "", path);
    }
    setCurrentPath(path);
    setProfileFocusSection(focusSection);
    setIsUserMenuOpen(false);
  }

  useEffect(() => {
    function handlePopState() {
      setCurrentPath(window.location.pathname || "/");
      setIsUserMenuOpen(false);
    }

    window.addEventListener("popstate", handlePopState);
    return () => {
      window.removeEventListener("popstate", handlePopState);
    };
  }, []);

  useEffect(() => {
    if (!isUserMenuOpen) {
      return;
    }

    function handlePointerDown(event) {
      if (
        userMenuWrapRef.current &&
        !userMenuWrapRef.current.contains(event.target)
      ) {
        setIsUserMenuOpen(false);
      }
    }

    function handleEscape(event) {
      if (event.key === "Escape") {
        setIsUserMenuOpen(false);
      }
    }

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleEscape);

    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [isUserMenuOpen]);

  useEffect(() => {
    const hasStoredToken = Boolean(localStorage.getItem(TOKEN_STORAGE_KEY));
    if (
      !currentAccount &&
      !isSessionLoading &&
      !hasStoredToken &&
      currentPath === "/profile"
    ) {
      if (typeof window !== "undefined") {
        window.history.replaceState({}, "", "/");
      }
      setCurrentPath("/");
    }
  }, [currentAccount, currentPath, isSessionLoading]);

  useEffect(() => {
    if (!currentAccount) {
      setProfileUpdateDraft(EMPTY_PROFILE_UPDATE_DRAFT);
      return;
    }

    setProfileUpdateDraft((previous) => ({
      ...previous,
      cityId:
        currentAccount.city_id != null ? String(currentAccount.city_id) : "",
      currentPassword: "",
      newPassword: "",
    }));
  }, [currentAccount]);

  useEffect(() => {
    if (!isProfilePage || profileFocusSection !== "settings") {
      return;
    }

    const settingsCard = document.getElementById("profile-settings-card");
    settingsCard?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [isProfilePage, profileFocusSection]);

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
          searchQuery: studentFilters.teacherSearch || undefined,
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
    studentFilters.teacherSearch,
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
      setTeacherSlotBookingsBySlotId({});
      setExpandedTeacherSlotId(null);
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
      setAdminAccountsSkip(0);
      setHasMoreAdminAccounts(false);
      return;
    }

    async function loadAccounts() {
      setIsAdminAccountsLoading(true);

      try {
        await loadAdminAccountsPage(adminAccountsSkip);
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
  }, [adminAccountsSkip, role]);

  useEffect(() => {
    if (role !== "admin") {
      setOverviewAnalytics(null);
      setTeacherAnalyticsRows([]);
      setDisciplineAnalyticsRows([]);
      return;
    }

    async function loadAdminAnalytics() {
      setIsAdminAnalyticsLoading(true);

      const analyticsQuery = {
        cityId: adminAnalyticsFilters.cityId || undefined,
        disciplineId: adminAnalyticsFilters.disciplineId || undefined,
        teacherId: adminAnalyticsFilters.teacherId || undefined,
        startsFrom: adminAnalyticsFilters.startsFrom
          ? toIsoFromLocalInput(adminAnalyticsFilters.startsFrom)
          : undefined,
        endsTo: adminAnalyticsFilters.endsTo
          ? toIsoFromLocalInput(adminAnalyticsFilters.endsTo)
          : undefined,
      };

      try {
        const [overview, teacherRows, disciplineRows] = await Promise.all([
          getOverviewAnalytics(analyticsQuery),
          listTeacherAnalytics(analyticsQuery),
          listDisciplineAnalytics(analyticsQuery),
        ]);

        setOverviewAnalytics(overview);
        setTeacherAnalyticsRows(teacherRows);
        setDisciplineAnalyticsRows(disciplineRows);
      } catch (error) {
        setNotice({
          kind: "error",
          text: `Не вдалося завантажити admin-аналітику: ${error.message}`,
        });
      } finally {
        setIsAdminAnalyticsLoading(false);
      }
    }

    void loadAdminAnalytics();
  }, [
    adminAnalyticsFilters.cityId,
    adminAnalyticsFilters.disciplineId,
    adminAnalyticsFilters.endsTo,
    adminAnalyticsFilters.startsFrom,
    adminAnalyticsFilters.teacherId,
    role,
  ]);

  function setSessionFromTokenPayload(payload) {
    localStorage.setItem(TOKEN_STORAGE_KEY, payload.access_token);
    setAccessToken(payload.access_token);
    setCurrentAccount({
      user_id: payload.user_id,
      username: payload.username,
      role: payload.role,
      student_id: payload.student_id,
      teacher_id: payload.teacher_id,
      full_name: null,
      email: null,
      city_id: null,
      city_name: null,
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
    setIsUserMenuOpen(false);
    setProfileUpdateDraft(EMPTY_PROFILE_UPDATE_DRAFT);
    setReviewEditorBookingId(null);
    setReviewDraftByBookingId({});
    if (typeof window !== "undefined") {
      window.history.replaceState({}, "", "/");
    }
    setCurrentPath("/");
    setBookings([]);
    setTeacherSlots([]);
    setTeacherSlotBookingsBySlotId({});
    setExpandedTeacherSlotId(null);
    setAdminAnalyticsFilters(EMPTY_ADMIN_ANALYTICS_FILTERS);
    setOverviewAnalytics(null);
    setTeacherAnalyticsRows([]);
    setDisciplineAnalyticsRows([]);
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

  function validateStudentRegistrationDraft() {
    const username = studentRegisterDraft.username.trim();
    const password = studentRegisterDraft.password;
    const fullName = studentRegisterDraft.fullName.trim();
    const email = studentRegisterDraft.email.trim();

    if (username.length < 3) {
      return "Username має містити щонайменше 3 символи.";
    }
    if (password.length < 6) {
      return "Password має містити щонайменше 6 символів.";
    }
    if (!fullName) {
      return "Вкажіть повне ім'я.";
    }
    if (!email.includes("@")) {
      return "Вкажіть коректний email.";
    }
    if (!studentRegisterDraft.cityId) {
      return "Оберіть місто для реєстрації.";
    }

    return null;
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

  function handleAdminAnalyticsFilterChange(event) {
    const { name, value } = event.target;
    setAdminAnalyticsFilters((previous) => {
      if (name === "cityId" && previous.teacherId) {
        return {
          ...previous,
          [name]: value,
          teacherId: "",
        };
      }

      return { ...previous, [name]: value };
    });
  }

  function handleProfileUpdateDraftChange(event) {
    const { name, value } = event.target;
    setProfileUpdateDraft((previous) => ({ ...previous, [name]: value }));
  }

  async function handleProfileUpdate(event) {
    event.preventDefault();

    if (!currentAccount) {
      return;
    }

    const currentPassword = profileUpdateDraft.currentPassword.trim();
    const newPassword = profileUpdateDraft.newPassword.trim();

    const hasOnlyOnePasswordField =
      (currentPassword && !newPassword) || (!currentPassword && newPassword);

    if (hasOnlyOnePasswordField) {
      setNotice({
        kind: "warning",
        text: "Щоб змінити пароль, заповніть і поточний, і новий пароль.",
      });
      return;
    }

    const cityChanged =
      canEditProfileCity &&
      profileUpdateDraft.cityId &&
      String(currentAccount.city_id ?? "") !==
        String(profileUpdateDraft.cityId);
    const wantsPasswordUpdate = Boolean(currentPassword && newPassword);

    if (!cityChanged && !wantsPasswordUpdate) {
      setNotice({
        kind: "warning",
        text:
          role === "admin"
            ? "Для admin доступна лише зміна пароля. Заповніть обидва поля пароля."
            : "Немає змін для оновлення профілю.",
      });
      return;
    }

    setIsProfileSubmitting(true);

    try {
      const updatedAccount = await updateCurrentAccount({
        cityId: cityChanged ? profileUpdateDraft.cityId : undefined,
        currentPassword: currentPassword || undefined,
        newPassword: newPassword || undefined,
      });

      setCurrentAccount(updatedAccount);
      setProfileUpdateDraft({
        cityId:
          updatedAccount.city_id != null ? String(updatedAccount.city_id) : "",
        currentPassword: "",
        newPassword: "",
      });

      if (role === "student" && cityChanged) {
        setStudentFilters((previous) => ({
          ...previous,
          cityId: String(updatedAccount.city_id ?? previous.cityId),
          teacherId: "",
        }));
      }

      setNotice({ kind: "success", text: "Профіль оновлено." });
    } catch (error) {
      setNotice({
        kind: "error",
        text: `Не вдалося оновити профіль: ${error.message}`,
      });
    } finally {
      setIsProfileSubmitting(false);
    }
  }

  function handleReviewDraftChange(bookingId, field, value) {
    setReviewDraftByBookingId((previous) => ({
      ...previous,
      [bookingId]: {
        ...(previous[bookingId] ?? EMPTY_REVIEW_DRAFT),
        [field]: value,
      },
    }));
  }

  async function handleSubmitReview(booking) {
    const reviewDraft =
      reviewDraftByBookingId[booking.booking_id] ?? EMPTY_REVIEW_DRAFT;
    const rating = Number(reviewDraft.rating);

    if (!Number.isInteger(rating) || rating < 1 || rating > 5) {
      setNotice({
        kind: "warning",
        text: "Рейтинг має бути від 1 до 5.",
      });
      return;
    }

    setReviewSubmittingBookingId(booking.booking_id);

    try {
      await createReview({
        teacherId: booking.teacher_id,
        rating,
        comment: reviewDraft.comment?.trim() || undefined,
      });

      const [loadedBookings, loadedTeachers] = await Promise.all([
        listBookings(),
        listTeachers({
          cityId: studentFilters.cityId || undefined,
          disciplineId: studentFilters.disciplineId || undefined,
          searchQuery: studentFilters.teacherSearch || undefined,
        }),
      ]);
      setBookings(loadedBookings);
      setTeachers(loadedTeachers);

      setReviewDraftByBookingId((previous) => {
        const updated = { ...previous };
        delete updated[booking.booking_id];
        return updated;
      });
      setReviewEditorBookingId(null);
      setNotice({ kind: "success", text: "Відгук збережено." });
    } catch (error) {
      setNotice({
        kind: "error",
        text: `Не вдалося залишити відгук: ${error.message}`,
      });
    } finally {
      setReviewSubmittingBookingId(null);
    }
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

    const validationError = validateStudentRegistrationDraft();
    if (validationError) {
      setNotice({ kind: "warning", text: validationError });
      return;
    }

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

  async function loadTeacherSlotBookings(slotId) {
    setTeacherBookingsLoadingSlotId(slotId);

    try {
      const rows = await listTeacherSlotBookings(slotId);
      setTeacherSlotBookingsBySlotId((previous) => ({
        ...previous,
        [slotId]: rows,
      }));
    } catch (error) {
      setNotice({
        kind: "error",
        text: `Не вдалося завантажити записи на слот: ${error.message}`,
      });
    } finally {
      setTeacherBookingsLoadingSlotId(null);
    }
  }

  async function handleToggleTeacherBookings(slotId) {
    setExpandedTeacherSlotId(slotId);
    await loadTeacherSlotBookings(slotId);
  }

  async function handleTeacherCancelBooking(slotId, bookingId) {
    const actionKey = `${slotId}:${bookingId}:cancel`;
    setTeacherBookingActionKey(actionKey);

    try {
      await cancelTeacherSlotBooking(slotId, bookingId);
      const [loadedSlots, slotBookings] = await Promise.all([
        listTeacherSlots(),
        listTeacherSlotBookings(slotId),
      ]);
      setTeacherSlots(loadedSlots);
      setTeacherSlotBookingsBySlotId((previous) => ({
        ...previous,
        [slotId]: slotBookings,
      }));
      setNotice({
        kind: "success",
        text: "Запис студента скасовано викладачем.",
      });
    } catch (error) {
      setNotice({
        kind: "error",
        text: `Не вдалося скасувати запис студента: ${error.message}`,
      });
    } finally {
      setTeacherBookingActionKey(null);
    }
  }

  async function handleTeacherCompleteBooking(slotId, bookingId) {
    const actionKey = `${slotId}:${bookingId}:complete`;
    setTeacherBookingActionKey(actionKey);

    try {
      await completeTeacherSlotBooking(slotId, bookingId);
      const [loadedSlots, slotBookings] = await Promise.all([
        listTeacherSlots(),
        listTeacherSlotBookings(slotId),
      ]);
      setTeacherSlots(loadedSlots);
      setTeacherSlotBookingsBySlotId((previous) => ({
        ...previous,
        [slotId]: slotBookings,
      }));
      setNotice({ kind: "success", text: "Запис позначено як завершений." });
    } catch (error) {
      setNotice({
        kind: "error",
        text: `Не вдалося завершити запис: ${error.message}`,
      });
    } finally {
      setTeacherBookingActionKey(null);
    }
  }

  async function handleCreateTeacherAccount(event) {
    event.preventDefault();

    const username = teacherAccountForm.username.trim().toLowerCase();
    const password = teacherAccountForm.password;

    if (username.length < 3) {
      setNotice({
        kind: "warning",
        text: "Username має містити щонайменше 3 символи.",
      });
      return;
    }

    if (password.length < 6) {
      setNotice({
        kind: "warning",
        text: "Password має містити щонайменше 6 символів.",
      });
      return;
    }

    if (!teacherAccountForm.teacherId) {
      setNotice({
        kind: "warning",
        text: "Оберіть профіль викладача для прив'язки акаунта.",
      });
      return;
    }

    if (teacherDirectory.length === 0) {
      setNotice({
        kind: "warning",
        text: "Немає профілів викладачів для прив'язки акаунта.",
      });
      return;
    }

    setIsAdminAccountsLoading(true);

    try {
      await createTeacherAccount({
        username,
        password,
        teacherId: teacherAccountForm.teacherId,
      });

      if (adminAccountsSkip !== 0) {
        setAdminAccountsSkip(0);
      } else {
        await loadAdminAccountsPage(0);
      }

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
  const adminOverview = overviewAnalytics ?? {
    total_cities: 0,
    total_disciplines: 0,
    total_teachers: 0,
    total_students: 0,
    filtered_slots_total: 0,
    filtered_slots_active: 0,
    filtered_bookings_total: 0,
    filtered_capacity_total: 0,
    filtered_reserved_seats_total: 0,
    utilization_rate_percent: 0,
  };

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
          <div className="top-nav-main">
            <p className="meta-line">
              Увійшли як <strong>{userDisplayName}</strong>
            </p>
            <p className="meta-line role-line">Роль: {currentAccount.role}</p>
          </div>

          <div className="top-nav-menu-wrap" ref={userMenuWrapRef}>
            <button
              type="button"
              className="avatar-button"
              aria-haspopup="menu"
              aria-expanded={isUserMenuOpen}
              aria-controls="user-menu-dropdown"
              onClick={() => setIsUserMenuOpen((previous) => !previous)}
            >
              {userInitials}
            </button>

            {isUserMenuOpen ? (
              <div className="user-menu-dropdown" id="user-menu-dropdown">
                <button
                  type="button"
                  className="ghost"
                  onClick={() => navigateTo("/profile", "profile")}
                >
                  Мій профіль
                </button>
                <button
                  type="button"
                  className="ghost"
                  onClick={() => navigateTo("/profile", "settings")}
                >
                  Налаштування
                </button>
                <button type="button" className="danger" onClick={handleLogout}>
                  Вийти
                </button>
              </div>
            ) : null}
          </div>
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
        </section>
      ) : null}

      {currentAccount && isProfilePage ? (
        <section className="two-column">
          <article className="panel reveal" style={{ animationDelay: "180ms" }}>
            <h2>Мій профіль</h2>
            <p className="meta-line">Username: {currentAccount.username}</p>
            <p className="meta-line">Роль: {currentAccount.role}</p>
            <p className="meta-line">
              ПІБ: {currentAccount.full_name ?? "Немає прив'язаного профілю"}
            </p>
            <p className="meta-line">
              Email: {currentAccount.email ?? "Не вказано"}
            </p>
            <p className="meta-line">
              Місто: {currentAccount.city_name ?? "Не вказано"}
            </p>

            <div className="inline-actions profile-actions-row">
              <button
                type="button"
                className={
                  profileFocusSection === "profile"
                    ? "ghost is-active"
                    : "ghost"
                }
                onClick={() => setProfileFocusSection("profile")}
              >
                Профіль
              </button>
              <button
                type="button"
                className={
                  profileFocusSection === "settings"
                    ? "ghost is-active"
                    : "ghost"
                }
                onClick={() => setProfileFocusSection("settings")}
              >
                Налаштування
              </button>
              <button
                type="button"
                className="ghost"
                onClick={() => navigateTo("/")}
              >
                Повернутися на головну
              </button>
            </div>
          </article>

          <article
            id="profile-settings-card"
            className="panel reveal"
            style={{ animationDelay: "240ms" }}
          >
            <h2>Налаштування облікового запису</h2>
            <form className="profile-form" onSubmit={handleProfileUpdate}>
              {canEditProfileCity ? (
                <label>
                  Місто
                  <select
                    name="cityId"
                    value={profileUpdateDraft.cityId}
                    onChange={handleProfileUpdateDraftChange}
                    disabled={isProfileSubmitting}
                  >
                    <option value="">Оберіть місто</option>
                    {cities.map((city) => (
                      <option key={city.id} value={city.id}>
                        {city.name}
                      </option>
                    ))}
                  </select>
                </label>
              ) : (
                <p className="hint-text">
                  Для ролі admin місто не змінюється. Тут доступна лише зміна
                  пароля.
                </p>
              )}

              <p className="meta-line">
                Щоб змінити пароль, заповніть обидва поля.
              </p>

              <label>
                Поточний пароль
                <input
                  name="currentPassword"
                  type="password"
                  value={profileUpdateDraft.currentPassword}
                  onChange={handleProfileUpdateDraftChange}
                  placeholder="Введіть поточний пароль"
                  autoComplete="current-password"
                />
              </label>

              <label>
                Новий пароль
                <input
                  name="newPassword"
                  type="password"
                  value={profileUpdateDraft.newPassword}
                  onChange={handleProfileUpdateDraftChange}
                  placeholder="Новий пароль (не менше 6 символів)"
                  autoComplete="new-password"
                />
              </label>

              <button type="submit" disabled={isProfileSubmitting}>
                {isProfileSubmitting ? "Оновлюю..." : "Зберегти зміни"}
              </button>
            </form>
          </article>
        </section>
      ) : null}

      {currentAccount?.role === "student" && !isProfilePage ? (
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
                        {teacher.average_rating != null
                          ? ` · ⭐ ${teacher.average_rating}`
                          : ""}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  Пошук за ім'ям викладача
                  <input
                    name="teacherSearch"
                    value={studentFilters.teacherSearch}
                    onChange={handleStudentFilterChange}
                    placeholder="Наприклад: Іван"
                  />
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
                {availableSlots.map((slot, index) => {
                  const hasActiveBooking = activeStudentBookingSlotIds.has(
                    slot.slot_id,
                  );

                  return (
                    <article
                      className="slot-card"
                      key={slot.slot_id}
                      style={{ animationDelay: `${index * 70 + 180}ms` }}
                    >
                      <p className="slot-topic">{slot.discipline_name}</p>
                      <h3>{slot.teacher_name}</h3>
                      {teacherRatingById.has(slot.teacher_id) ? (
                        <p className="slot-meta">
                          ⭐ Рейтинг: {teacherRatingById.get(slot.teacher_id)}
                        </p>
                      ) : null}
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
                          slot.available_seats <= 0 ||
                          hasActiveBooking
                        }
                      >
                        {bookingInProgressSlotId === slot.slot_id
                          ? "Бронюю..."
                          : hasActiveBooking
                            ? "Вже записані"
                            : slot.available_seats <= 0
                              ? "Немає місць"
                              : "Записатися"}
                      </button>
                    </article>
                  );
                })}
              </div>
            )}
          </section>

          <section className="panel reveal" style={{ animationDelay: "420ms" }}>
            <div className="panel-header-row">
              <h2>Мої бронювання</h2>
              <span className="badge">
                {isBookingsLoading
                  ? "Оновлення..."
                  : `У списку: ${shownBookings.length}`}
              </span>
            </div>

            <div className="inline-actions booking-tabs-row">
              <button
                type="button"
                className={
                  studentBookingTab === "upcoming" ? "ghost is-active" : "ghost"
                }
                onClick={() => setStudentBookingTab("upcoming")}
              >
                Майбутні заняття ({upcomingBookings.length})
              </button>
              <button
                type="button"
                className={
                  studentBookingTab === "history" ? "ghost is-active" : "ghost"
                }
                onClick={() => setStudentBookingTab("history")}
              >
                Історія ({historyBookings.length})
              </button>
            </div>

            {shownBookings.length === 0 && !isBookingsLoading ? (
              <p className="empty-state">
                {studentBookingTab === "upcoming"
                  ? "Поки що немає активних бронювань."
                  : "Історія записів поки порожня."}
              </p>
            ) : (
              <div className="booking-list">
                {shownBookings.map((booking, index) => (
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
                      <p className="slot-meta">
                        Статус:{" "}
                        {String(booking.status ?? "active").toUpperCase()}
                      </p>

                      {booking.status === "completed" && booking.has_review ? (
                        <p className="meta-line review-done-text">
                          Відгук уже залишено.
                        </p>
                      ) : null}

                      {booking.status === "completed" &&
                      !booking.has_review &&
                      reviewEditorBookingId === booking.booking_id ? (
                        <form
                          className="review-form"
                          onSubmit={(event) => {
                            event.preventDefault();
                            void handleSubmitReview(booking);
                          }}
                        >
                          <label>
                            Рейтинг
                            <select
                              value={
                                (
                                  reviewDraftByBookingId[booking.booking_id] ??
                                  EMPTY_REVIEW_DRAFT
                                ).rating
                              }
                              onChange={(event) =>
                                handleReviewDraftChange(
                                  booking.booking_id,
                                  "rating",
                                  event.target.value,
                                )
                              }
                            >
                              <option value="5">5 - Відмінно</option>
                              <option value="4">4 - Добре</option>
                              <option value="3">3 - Нормально</option>
                              <option value="2">2 - Погано</option>
                              <option value="1">1 - Дуже погано</option>
                            </select>
                          </label>

                          <label>
                            Коментар
                            <input
                              value={
                                (
                                  reviewDraftByBookingId[booking.booking_id] ??
                                  EMPTY_REVIEW_DRAFT
                                ).comment
                              }
                              onChange={(event) =>
                                handleReviewDraftChange(
                                  booking.booking_id,
                                  "comment",
                                  event.target.value,
                                )
                              }
                              placeholder="Короткий відгук про заняття"
                            />
                          </label>

                          <div className="inline-actions">
                            <button
                              type="submit"
                              disabled={
                                reviewSubmittingBookingId === booking.booking_id
                              }
                            >
                              {reviewSubmittingBookingId === booking.booking_id
                                ? "Зберігаю..."
                                : "Підтвердити відгук"}
                            </button>
                            <button
                              type="button"
                              className="ghost"
                              onClick={() => setReviewEditorBookingId(null)}
                            >
                              Скасувати
                            </button>
                          </div>
                        </form>
                      ) : null}
                    </div>

                    <div className="inline-actions">
                      <button
                        type="button"
                        className="ghost"
                        onClick={() =>
                          void handleCancelBooking(booking.booking_id)
                        }
                        disabled={
                          cancelInProgressBookingId === booking.booking_id ||
                          booking.status !== "active"
                        }
                      >
                        {booking.status !== "active"
                          ? "Недоступно"
                          : cancelInProgressBookingId === booking.booking_id
                            ? "Скасовую..."
                            : "Скасувати"}
                      </button>

                      {booking.status === "completed" && !booking.has_review ? (
                        <button
                          type="button"
                          className="ghost"
                          onClick={() =>
                            setReviewEditorBookingId(booking.booking_id)
                          }
                        >
                          Залишити відгук
                        </button>
                      ) : null}
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>
        </>
      ) : null}

      {currentAccount?.role === "teacher" && !isProfilePage ? (
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
                        onClick={() =>
                          void handleToggleTeacherBookings(slot.slot_id)
                        }
                        disabled={teacherBookingsLoadingSlotId === slot.slot_id}
                      >
                        {expandedTeacherSlotId === slot.slot_id
                          ? "Оновити деталі"
                          : "Деталі слота"}
                      </button>
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

          {expandedTeacherSlotId != null ? (
            <div className="modal-overlay" role="dialog" aria-modal="true">
              <div className="modal-card">
                <div className="panel-header-row">
                  <h2>Деталі слота #{expandedTeacherSlotId}</h2>
                  <button
                    type="button"
                    className="ghost"
                    onClick={() => setExpandedTeacherSlotId(null)}
                  >
                    Закрити
                  </button>
                </div>

                {expandedTeacherSlot ? (
                  <div className="modal-summary-grid">
                    <p className="meta-line">
                      Дисципліна:{" "}
                      <strong>{expandedTeacherSlot.discipline_name}</strong>
                    </p>
                    <p className="meta-line">
                      Час:{" "}
                      {formatDateTimeRange(
                        expandedTeacherSlot.starts_at,
                        expandedTeacherSlot.ends_at,
                      )}
                    </p>
                    <p className="meta-line">
                      Місць: {expandedTeacherSlot.available_seats}/
                      {expandedTeacherSlot.capacity}
                    </p>
                    <p className="meta-line">
                      Статус:{" "}
                      {expandedTeacherSlot.is_active
                        ? "Активний"
                        : "Неактивний"}
                    </p>
                  </div>
                ) : null}

                <h3>Записані студенти</h3>

                {teacherBookingsLoadingSlotId === expandedTeacherSlotId ? (
                  <p className="meta-line">Завантажую записи...</p>
                ) : expandedTeacherSlotBookings.length === 0 ? (
                  <p className="empty-state">Немає записів для цього слота.</p>
                ) : (
                  <div className="table-wrap">
                    <table className="slot-bookings-table">
                      <thead>
                        <tr>
                          <th>Ім'я</th>
                          <th>Email</th>
                          <th>Статус</th>
                          <th>Дії</th>
                        </tr>
                      </thead>
                      <tbody>
                        {expandedTeacherSlotBookings.map((booking) => (
                          <tr key={booking.booking_id}>
                            <td>{booking.student_name}</td>
                            <td>{booking.student_email}</td>
                            <td>{String(booking.status).toUpperCase()}</td>
                            <td>
                              <div className="inline-actions">
                                <button
                                  type="button"
                                  className="ghost"
                                  onClick={() =>
                                    void handleTeacherCompleteBooking(
                                      expandedTeacherSlotId,
                                      booking.booking_id,
                                    )
                                  }
                                  disabled={
                                    teacherBookingActionKey ===
                                      `${expandedTeacherSlotId}:${booking.booking_id}:complete` ||
                                    booking.status !== "active"
                                  }
                                >
                                  Завершити
                                </button>
                                <button
                                  type="button"
                                  className="danger"
                                  onClick={() =>
                                    void handleTeacherCancelBooking(
                                      expandedTeacherSlotId,
                                      booking.booking_id,
                                    )
                                  }
                                  disabled={
                                    teacherBookingActionKey ===
                                      `${expandedTeacherSlotId}:${booking.booking_id}:cancel` ||
                                    booking.status !== "active"
                                  }
                                >
                                  Скасувати
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          ) : null}
        </>
      ) : null}

      {currentAccount?.role === "admin" && !isProfilePage ? (
        <>
          <section className="panel reveal" style={{ animationDelay: "200ms" }}>
            <div className="panel-header-row">
              <h2>Admin аналітика</h2>
              <span className="badge">
                {isAdminAnalyticsLoading ? "Оновлення..." : "Актуально"}
              </span>
            </div>

            <div className="filters-grid admin-analytics-filters">
              <label>
                Місто
                <select
                  name="cityId"
                  value={adminAnalyticsFilters.cityId}
                  onChange={handleAdminAnalyticsFilterChange}
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
                  value={adminAnalyticsFilters.disciplineId}
                  onChange={handleAdminAnalyticsFilterChange}
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
                  value={adminAnalyticsFilters.teacherId}
                  onChange={handleAdminAnalyticsFilterChange}
                >
                  <option value="">Усі викладачі</option>
                  {teacherDirectory
                    .filter((teacher) => {
                      if (!adminAnalyticsFilters.cityId) {
                        return true;
                      }
                      return (
                        teacher.city_id === Number(adminAnalyticsFilters.cityId)
                      );
                    })
                    .map((teacher) => (
                      <option key={teacher.id} value={teacher.id}>
                        {teacher.full_name}
                      </option>
                    ))}
                </select>
              </label>

              <label>
                Початок інтервалу
                <input
                  name="startsFrom"
                  type="datetime-local"
                  value={adminAnalyticsFilters.startsFrom}
                  onChange={handleAdminAnalyticsFilterChange}
                />
              </label>

              <label>
                Кінець інтервалу
                <input
                  name="endsTo"
                  type="datetime-local"
                  value={adminAnalyticsFilters.endsTo}
                  onChange={handleAdminAnalyticsFilterChange}
                />
              </label>
            </div>

            <div className="analytics-kpi-grid">
              <article className="analytics-kpi-card">
                <p className="analytics-kpi-label">Слоти / активні</p>
                <p className="analytics-kpi-value">
                  {adminOverview.filtered_slots_total} /{" "}
                  {adminOverview.filtered_slots_active}
                </p>
              </article>
              <article className="analytics-kpi-card">
                <p className="analytics-kpi-label">Бронювання</p>
                <p className="analytics-kpi-value">
                  {adminOverview.filtered_bookings_total}
                </p>
              </article>
              <article className="analytics-kpi-card">
                <p className="analytics-kpi-label">Місткість</p>
                <p className="analytics-kpi-value">
                  {adminOverview.filtered_capacity_total}
                </p>
              </article>
              <article className="analytics-kpi-card">
                <p className="analytics-kpi-label">Зайняті місця</p>
                <p className="analytics-kpi-value">
                  {adminOverview.filtered_reserved_seats_total}
                </p>
              </article>
              <article className="analytics-kpi-card">
                <p className="analytics-kpi-label">Завантаження</p>
                <p className="analytics-kpi-value">
                  {adminOverview.utilization_rate_percent}%
                </p>
              </article>
            </div>
          </section>

          <section className="two-column">
            <article
              className="panel reveal"
              style={{ animationDelay: "240ms" }}
            >
              <h2>Створення акаунта викладача</h2>
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
                  Профіль викладача (існуючий)
                  <select
                    name="teacherId"
                    value={teacherAccountForm.teacherId}
                    onChange={handleTeacherAccountChange}
                    disabled={teacherDirectory.length === 0}
                  >
                    <option value="">Оберіть викладача</option>
                    {teacherDirectory.map((teacher) => (
                      <option key={teacher.id} value={teacher.id}>
                        {teacher.full_name}
                        {teacher.city_name ? ` · ${teacher.city_name}` : ""}
                      </option>
                    ))}
                  </select>
                </label>

                <p className="hint-text">
                  Цей крок створює логін/пароль і прив'язує акаунт до вже
                  наявного профілю викладача.
                </p>

                {teacherDirectory.length === 0 ? (
                  <p className="empty-state">
                    Немає доступних профілів викладачів. Спочатку створіть
                    профіль викладача в системі.
                  </p>
                ) : null}

                <button
                  type="submit"
                  disabled={isAdminAccountsLoading || teacherDirectory.length === 0}
                >
                  Створити акаунт доступу
                </button>
              </form>
            </article>

            <article
              className="panel reveal"
              style={{ animationDelay: "300ms" }}
            >
              <div className="panel-header-row">
                <h2>Усі акаунти</h2>
                <span className="badge">
                  {isAdminAccountsLoading
                    ? "Оновлення..."
                    : `На сторінці: ${accounts.length}`}
                </span>
              </div>

              <p className="meta-line">
                Сторінка{" "}
                {Math.floor(adminAccountsSkip / ADMIN_ACCOUNTS_PAGE_SIZE) + 1}
              </p>

              <div className="inline-actions">
                <button
                  type="button"
                  className="ghost"
                  onClick={() =>
                    setAdminAccountsSkip((previous) =>
                      Math.max(previous - ADMIN_ACCOUNTS_PAGE_SIZE, 0),
                    )
                  }
                  disabled={isAdminAccountsLoading || adminAccountsSkip === 0}
                >
                  Попередня сторінка
                </button>
                <button
                  type="button"
                  className="ghost"
                  onClick={() =>
                    setAdminAccountsSkip(
                      (previous) => previous + ADMIN_ACCOUNTS_PAGE_SIZE,
                    )
                  }
                  disabled={isAdminAccountsLoading || !hasMoreAdminAccounts}
                >
                  Наступна сторінка
                </button>
              </div>

              {accounts.length === 0 && !isAdminAccountsLoading ? (
                <p className="empty-state">
                  Акаунти не знайдено для цієї сторінки.
                </p>
              ) : (
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
              )}
            </article>
          </section>

          <section className="two-column">
            <article
              className="panel reveal"
              style={{ animationDelay: "340ms" }}
            >
              <h2>Топ викладачів</h2>
              {teacherAnalyticsRows.length === 0 && !isAdminAnalyticsLoading ? (
                <p className="empty-state">
                  Немає даних за поточними фільтрами.
                </p>
              ) : (
                <div className="analytics-list">
                  {teacherAnalyticsRows.slice(0, 8).map((row) => (
                    <article key={row.teacher_id} className="analytics-item">
                      <p>
                        <strong>{row.teacher_name}</strong> · {row.city_name}
                      </p>
                      <p className="meta-line">
                        Слоти: {row.slots_total} · Бронювання:{" "}
                        {row.bookings_total}
                      </p>
                      <p className="meta-line">
                        Завантаження: {row.utilization_rate_percent}%
                      </p>
                    </article>
                  ))}
                </div>
              )}
            </article>

            <article
              className="panel reveal"
              style={{ animationDelay: "400ms" }}
            >
              <h2>Попит за дисциплінами</h2>
              {disciplineAnalyticsRows.length === 0 &&
              !isAdminAnalyticsLoading ? (
                <p className="empty-state">
                  Немає даних за поточними фільтрами.
                </p>
              ) : (
                <div className="analytics-list">
                  {disciplineAnalyticsRows.slice(0, 8).map((row) => (
                    <article key={row.discipline_id} className="analytics-item">
                      <p>
                        <strong>{row.discipline_name}</strong>
                      </p>
                      <p className="meta-line">
                        Слоти: {row.slots_total} · Бронювання:{" "}
                        {row.bookings_total}
                      </p>
                      <p className="meta-line">
                        Завантаження: {row.utilization_rate_percent}%
                      </p>
                    </article>
                  ))}
                </div>
              )}
            </article>
          </section>
        </>
      ) : null}
    </div>
  );
}

export default App;
