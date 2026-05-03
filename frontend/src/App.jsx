import { useEffect, useMemo, useRef, useState } from "react";
import {
  clearMyNotifications,
  cancelTeacherSlotBooking,
  cancelBooking,
  clearAccessToken,
  completeAllTeacherSlotBookings,
  completeTeacherSlot,
  completeTeacherSlotBooking,
  createReview,
  createBooking,
  createTeacher,
  createTeacherAccount,
  createTeacherSlot,
  deleteTeacherSlot,
  getCurrentAccount,
  getOverviewAnalytics,
  listAccounts,
  listAvailableSlots,
  listBookings,
  listCities,
  listDisciplineAnalytics,
  listDisciplines,
  listMyNotifications,
  markNotificationAsRead,
  listTeacherReviews,
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
  formatDateTime,
  formatDateTimeRange,
  toDateTimeLocalInputValue,
  toIsoFromLocalInput,
} from "./lib/time";
import "./App.css";

const TOKEN_STORAGE_KEY = "distributor_access_token";
const ADMIN_ACCOUNTS_PAGE_SIZE = 5;
const ADMIN_ANALYTICS_PAGE_SIZE = 5;
const STUDENT_SLOTS_PAGE_SIZE = 6;
const TEACHER_SLOTS_PAGE_SIZE = 6;
const STUDENT_BOOKINGS_PAGE_SIZE = 6;
const EMAIL_REGEX = /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i;
const EMAIL_VALIDATION_MESSAGE =
  "Будь ласка, введіть коректну адресу електронної пошти (наприклад, example@gmail.com)";
const COMMON_EMAIL_DOMAIN_TYPOS = new Set([
  "gmail.co",
  "gmail.con",
  "gmai.com",
  "gmial.com",
  "gmal.com",
  "outlok.com",
  "outllok.com",
]);
const CANONICAL_EMAIL_PROVIDER_DOMAINS = {
  gmail: "gmail.com",
  outlook: "outlook.com",
};

function getTotalPages(itemsCount, pageSize) {
  return Math.max(Math.ceil(itemsCount / pageSize), 1);
}

function formatTeacherRatingSummary(averageRating, reviewsCount) {
  const normalizedReviewsCount = Number(reviewsCount ?? 0);
  if (averageRating == null || normalizedReviewsCount <= 0) {
    return "⭐ - (0)";
  }

  return `⭐ ${Number(averageRating).toFixed(1)} (${normalizedReviewsCount})`;
}

function getReviewStars(rating) {
  const safeRating = Math.max(Math.min(Number(rating) || 0, 5), 1);
  return "⭐".repeat(safeRating);
}

function getEmailValidationMessage(emailValue, { required = true } = {}) {
  const normalizedEmail = `${emailValue ?? ""}`.trim().toLowerCase();

  if (!normalizedEmail) {
    return required ? EMAIL_VALIDATION_MESSAGE : "";
  }

  if (!EMAIL_REGEX.test(normalizedEmail)) {
    return EMAIL_VALIDATION_MESSAGE;
  }

  const [, domain = ""] = normalizedEmail.split("@");
  if (COMMON_EMAIL_DOMAIN_TYPOS.has(domain)) {
    return EMAIL_VALIDATION_MESSAGE;
  }

  const providerLabel = domain.split(".", 1)[0];
  const canonicalDomain = CANONICAL_EMAIL_PROVIDER_DOMAINS[providerLabel];
  if (canonicalDomain && domain !== canonicalDomain) {
    return EMAIL_VALIDATION_MESSAGE;
  }

  return "";
}

const EMPTY_LOGIN = {
  username: "",
  password: "",
};

const EMPTY_STUDENT_REG = {
  username: "",
  password: "",
  confirmPassword: "",
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
  username: "",
  fullName: "",
  email: "",
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
  description: "",
  capacity: "1",
  isActive: true,
};

const EMPTY_TEACHER_REGISTRATION = {
  username: "",
  fullName: "",
  email: "",
  password: "",
  confirmPassword: "",
  cityId: "",
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
  const notificationsWrapRef = useRef(null);

  const [currentPath, setCurrentPath] = useState(() =>
    typeof window !== "undefined" ? window.location.pathname || "/" : "/",
  );
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [profileFocusSection, setProfileFocusSection] = useState("profile");

  const [cities, setCities] = useState([]);
  const [disciplines, setDisciplines] = useState([]);
  const [teachers, setTeachers] = useState([]);
  const [teacherDirectory, setTeacherDirectory] = useState([]);

  const [studentFilters, setStudentFilters] = useState(EMPTY_STUDENT_FILTERS);
  const [availableSlots, setAvailableSlots] = useState([]);
  const [studentSlotsPage, setStudentSlotsPage] = useState(1);
  const [hasMoreAvailableSlots, setHasMoreAvailableSlots] = useState(false);
  const [
    expandedAvailableSlotDescriptions,
    setExpandedAvailableSlotDescriptions,
  ] = useState({});
  const [expandedBookingDescriptions, setExpandedBookingDescriptions] =
    useState({});
  const [bookings, setBookings] = useState([]);

  const [teacherSlots, setTeacherSlots] = useState([]);
  const [teacherSlotBookingsBySlotId, setTeacherSlotBookingsBySlotId] =
    useState({});
  const [expandedTeacherSlotId, setExpandedTeacherSlotId] = useState(null);
  const [activeTeacherSlotsPage, setActiveTeacherSlotsPage] = useState(1);
  const [teacherSlotHistoryPage, setTeacherSlotHistoryPage] = useState(1);
  const [teacherBookingsLoadingSlotId, setTeacherBookingsLoadingSlotId] =
    useState(null);
  const [teacherBookingActionKey, setTeacherBookingActionKey] = useState(null);
  const [teacherSlotForm, setTeacherSlotForm] = useState(EMPTY_TEACHER_SLOT);
  const [editingSlotId, setEditingSlotId] = useState(null);
  const [editingSlotForm, setEditingSlotForm] = useState(EMPTY_TEACHER_SLOT);

  const [accounts, setAccounts] = useState([]);
  const [teacherRegistrationForm, setTeacherRegistrationForm] = useState(
    EMPTY_TEACHER_REGISTRATION,
  );
  const [adminAnalyticsFilters, setAdminAnalyticsFilters] = useState(
    EMPTY_ADMIN_ANALYTICS_FILTERS,
  );
  const [overviewAnalytics, setOverviewAnalytics] = useState(null);
  const [teacherAnalyticsRows, setTeacherAnalyticsRows] = useState([]);
  const [disciplineAnalyticsRows, setDisciplineAnalyticsRows] = useState([]);
  const [teacherAnalyticsPage, setTeacherAnalyticsPage] = useState(1);
  const [disciplineAnalyticsPage, setDisciplineAnalyticsPage] = useState(1);
  const [hasMoreTeacherAnalytics, setHasMoreTeacherAnalytics] = useState(false);
  const [hasMoreDisciplineAnalytics, setHasMoreDisciplineAnalytics] =
    useState(false);
  const [adminAccountsSkip, setAdminAccountsSkip] = useState(0);
  const [hasMoreAdminAccounts, setHasMoreAdminAccounts] = useState(false);
  const [profileUpdateDraft, setProfileUpdateDraft] = useState(
    EMPTY_PROFILE_UPDATE_DRAFT,
  );
  const [teacherReviews, setTeacherReviews] = useState([]);
  const [isTeacherReviewsLoading, setIsTeacherReviewsLoading] = useState(false);
  const [activeTeacherReviewTargetId, setActiveTeacherReviewTargetId] =
    useState(null);
  const [teacherDetailsModalContext, setTeacherDetailsModalContext] =
    useState(null);
  const [teacherDetailsModalReviews, setTeacherDetailsModalReviews] = useState(
    [],
  );
  const [
    isTeacherDetailsModalReviewsLoading,
    setIsTeacherDetailsModalReviewsLoading,
  ] = useState(false);
  const [
    showAllTeacherDetailsModalReviews,
    setShowAllTeacherDetailsModalReviews,
  ] = useState(false);

  const [studentBookingTab, setStudentBookingTab] = useState("upcoming");
  const [upcomingBookingsPage, setUpcomingBookingsPage] = useState(1);
  const [historyBookingsPage, setHistoryBookingsPage] = useState(1);
  const [reviewEditorBookingId, setReviewEditorBookingId] = useState(null);
  const [reviewDraftByBookingId, setReviewDraftByBookingId] = useState({});

  const [currentAccount, setCurrentAccount] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [isNotificationsLoading, setIsNotificationsLoading] = useState(false);
  const [notificationActionId, setNotificationActionId] = useState(null);
  const [isNotificationsClearing, setIsNotificationsClearing] = useState(false);

  const [loginDraft, setLoginDraft] = useState(EMPTY_LOGIN);
  const [studentRegisterDraft, setStudentRegisterDraft] =
    useState(EMPTY_STUDENT_REG);
  const [studentRegisterEmailError, setStudentRegisterEmailError] =
    useState("");
  const [teacherRegistrationEmailError, setTeacherRegistrationEmailError] =
    useState("");
  const [profileEmailError, setProfileEmailError] = useState("");

  const [isCatalogLoading, setIsCatalogLoading] = useState(true);
  const [isSessionLoading, setIsSessionLoading] = useState(false);
  const [isAuthSubmitting, setIsAuthSubmitting] = useState(false);
  const [isSlotsLoading, setIsSlotsLoading] = useState(false);
  const [isBookingsLoading, setIsBookingsLoading] = useState(false);
  const [isTeacherSlotsLoading, setIsTeacherSlotsLoading] = useState(false);
  const [isTeacherSlotSubmitting, setIsTeacherSlotSubmitting] = useState(false);
  const [isTeacherRegistrationSubmitting, setIsTeacherRegistrationSubmitting] =
    useState(false);
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
  const canEditProfileFullName = role === "student" || role === "teacher";
  const canEditProfileEmail = role === "student" || role === "teacher";
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

  const activeTeacherSlots = useMemo(
    () =>
      teacherSlots.filter((slot) => {
        const endsAtMs = Date.parse(slot.ends_at);
        return (
          slot.is_active && Number.isFinite(endsAtMs) && endsAtMs > Date.now()
        );
      }),
    [teacherSlots],
  );

  const teacherSlotHistory = useMemo(
    () =>
      teacherSlots.filter((slot) => {
        const endsAtMs = Date.parse(slot.ends_at);
        const hasEnded = !Number.isFinite(endsAtMs) || endsAtMs <= Date.now();
        return !slot.is_active || hasEnded;
      }),
    [teacherSlots],
  );

  const paginatedActiveTeacherSlots = useMemo(() => {
    const start = (activeTeacherSlotsPage - 1) * TEACHER_SLOTS_PAGE_SIZE;
    return activeTeacherSlots.slice(start, start + TEACHER_SLOTS_PAGE_SIZE);
  }, [activeTeacherSlots, activeTeacherSlotsPage]);

  const paginatedTeacherSlotHistory = useMemo(() => {
    const start = (teacherSlotHistoryPage - 1) * TEACHER_SLOTS_PAGE_SIZE;
    return teacherSlotHistory.slice(start, start + TEACHER_SLOTS_PAGE_SIZE);
  }, [teacherSlotHistory, teacherSlotHistoryPage]);

  const totalActiveTeacherSlotsPages = useMemo(
    () => getTotalPages(activeTeacherSlots.length, TEACHER_SLOTS_PAGE_SIZE),
    [activeTeacherSlots.length],
  );

  const totalTeacherSlotHistoryPages = useMemo(
    () => getTotalPages(teacherSlotHistory.length, TEACHER_SLOTS_PAGE_SIZE),
    [teacherSlotHistory.length],
  );

  const hasMoreActiveTeacherSlots =
    activeTeacherSlotsPage < totalActiveTeacherSlotsPages;
  const hasMoreTeacherSlotHistory =
    teacherSlotHistoryPage < totalTeacherSlotHistoryPages;

  const hasUnreadNotifications = useMemo(
    () => notifications.some((notification) => !notification.is_read),
    [notifications],
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
          value: activeTeacherSlots.length,
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
    activeTeacherSlots.length,
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

  const paginatedUpcomingBookings = useMemo(() => {
    const start = (upcomingBookingsPage - 1) * STUDENT_BOOKINGS_PAGE_SIZE;
    return upcomingBookings.slice(start, start + STUDENT_BOOKINGS_PAGE_SIZE);
  }, [upcomingBookings, upcomingBookingsPage]);

  const paginatedHistoryBookings = useMemo(() => {
    const start = (historyBookingsPage - 1) * STUDENT_BOOKINGS_PAGE_SIZE;
    return historyBookings.slice(start, start + STUDENT_BOOKINGS_PAGE_SIZE);
  }, [historyBookings, historyBookingsPage]);

  const totalUpcomingBookingsPages = useMemo(
    () => getTotalPages(upcomingBookings.length, STUDENT_BOOKINGS_PAGE_SIZE),
    [upcomingBookings.length],
  );

  const totalHistoryBookingsPages = useMemo(
    () => getTotalPages(historyBookings.length, STUDENT_BOOKINGS_PAGE_SIZE),
    [historyBookings.length],
  );

  const shownBookings =
    studentBookingTab === "upcoming"
      ? paginatedUpcomingBookings
      : paginatedHistoryBookings;

  const currentStudentBookingsPage =
    studentBookingTab === "upcoming"
      ? upcomingBookingsPage
      : historyBookingsPage;

  const hasMoreShownBookings =
    studentBookingTab === "upcoming"
      ? upcomingBookingsPage < totalUpcomingBookingsPages
      : historyBookingsPage < totalHistoryBookingsPages;

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

  const cityNameById = useMemo(
    () => new Map(cities.map((city) => [city.id, city.name])),
    [cities],
  );

  const displayedTeacherDetailsModalReviews = useMemo(() => {
    if (showAllTeacherDetailsModalReviews) {
      return teacherDetailsModalReviews;
    }

    return teacherDetailsModalReviews.slice(0, 5);
  }, [showAllTeacherDetailsModalReviews, teacherDetailsModalReviews]);

  const hasHiddenTeacherDetailsModalReviews =
    teacherDetailsModalReviews.length > 5;

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
    setIsNotificationsOpen(false);
  }

  useEffect(() => {
    function handlePopState() {
      setCurrentPath(window.location.pathname || "/");
      setIsUserMenuOpen(false);
      setIsNotificationsOpen(false);
    }

    window.addEventListener("popstate", handlePopState);
    return () => {
      window.removeEventListener("popstate", handlePopState);
    };
  }, []);

  useEffect(() => {
    if (!isUserMenuOpen && !isNotificationsOpen) {
      return;
    }

    function handlePointerDown(event) {
      const clickedInsideUserMenu = Boolean(
        userMenuWrapRef.current?.contains(event.target),
      );
      const clickedInsideNotifications = Boolean(
        notificationsWrapRef.current?.contains(event.target),
      );

      if (!clickedInsideUserMenu && !clickedInsideNotifications) {
        setIsUserMenuOpen(false);
        setIsNotificationsOpen(false);
      }
    }

    function handleEscape(event) {
      if (event.key === "Escape") {
        setIsUserMenuOpen(false);
        setIsNotificationsOpen(false);
      }
    }

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleEscape);

    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [isNotificationsOpen, isUserMenuOpen]);

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
      username: currentAccount.username ?? "",
      fullName: currentAccount.full_name ?? "",
      email: currentAccount.email ?? "",
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
    if (!currentAccount?.user_id) {
      setNotifications([]);
      setIsNotificationsOpen(false);
      return;
    }

    let isMounted = true;

    async function loadNotifications({ silent = false } = {}) {
      if (!silent) {
        setIsNotificationsLoading(true);
      }

      try {
        const rows = await listMyNotifications();
        if (isMounted) {
          setNotifications(rows);
        }
      } catch (error) {
        if (!silent && isMounted) {
          setNotice({
            kind: "error",
            text: `Не вдалося завантажити сповіщення: ${error.message}`,
          });
        }
      } finally {
        if (!silent && isMounted) {
          setIsNotificationsLoading(false);
        }
      }
    }

    void loadNotifications();

    const intervalId = window.setInterval(() => {
      void loadNotifications({ silent: true });
    }, 30000);

    return () => {
      isMounted = false;
      window.clearInterval(intervalId);
    };
  }, [currentAccount?.user_id]);

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
        setTeachers([]);
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
      return;
    }

    setStudentSlotsPage(1);
  }, [
    role,
    studentFilters.cityId,
    studentFilters.disciplineId,
    studentFilters.teacherId,
  ]);

  useEffect(() => {
    if (role !== "student") {
      setAvailableSlots([]);
      setHasMoreAvailableSlots(false);
      setExpandedAvailableSlotDescriptions({});
      return;
    }

    async function loadSlots() {
      setIsSlotsLoading(true);

      const skip = (studentSlotsPage - 1) * STUDENT_SLOTS_PAGE_SIZE;
      const baseQuery = {
        cityId: studentFilters.cityId || undefined,
        disciplineId: studentFilters.disciplineId || undefined,
        teacherId: studentFilters.teacherId || undefined,
      };

      try {
        const [slots, nextPageProbe] = await Promise.all([
          listAvailableSlots({
            ...baseQuery,
            skip,
            limit: STUDENT_SLOTS_PAGE_SIZE,
          }),
          listAvailableSlots({
            ...baseQuery,
            skip: skip + STUDENT_SLOTS_PAGE_SIZE,
            limit: 1,
          }),
        ]);

        if (studentSlotsPage > 1 && slots.length === 0) {
          setStudentSlotsPage((previous) => Math.max(previous - 1, 1));
          return;
        }

        setAvailableSlots(slots);
        setHasMoreAvailableSlots(nextPageProbe.length > 0);
        setExpandedAvailableSlotDescriptions({});
      } catch (error) {
        setAvailableSlots([]);
        setHasMoreAvailableSlots(false);
        setExpandedAvailableSlotDescriptions({});
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
    studentSlotsPage,
    studentFilters.cityId,
    studentFilters.disciplineId,
    studentFilters.teacherId,
  ]);

  useEffect(() => {
    if (role !== "student" || !studentId) {
      setBookings([]);
      setExpandedBookingDescriptions({});
      setUpcomingBookingsPage(1);
      setHistoryBookingsPage(1);
      return;
    }

    async function loadBookings() {
      setIsBookingsLoading(true);

      try {
        const loadedBookings = await listBookings();
        setBookings(loadedBookings);
        setExpandedBookingDescriptions({});
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
    if (role !== "student") {
      return;
    }

    setUpcomingBookingsPage((previous) =>
      Math.min(previous, totalUpcomingBookingsPages),
    );
    setHistoryBookingsPage((previous) =>
      Math.min(previous, totalHistoryBookingsPages),
    );
  }, [role, totalHistoryBookingsPages, totalUpcomingBookingsPages]);

  useEffect(() => {
    if (role !== "teacher") {
      setTeacherSlots([]);
      setTeacherSlotBookingsBySlotId({});
      setExpandedTeacherSlotId(null);
      setActiveTeacherSlotsPage(1);
      setTeacherSlotHistoryPage(1);
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
    if (role !== "teacher") {
      return;
    }

    setActiveTeacherSlotsPage((previous) =>
      Math.min(previous, totalActiveTeacherSlotsPages),
    );
    setTeacherSlotHistoryPage((previous) =>
      Math.min(previous, totalTeacherSlotHistoryPages),
    );
  }, [role, totalActiveTeacherSlotsPages, totalTeacherSlotHistoryPages]);

  useEffect(() => {
    if (role !== "teacher") {
      setTeacherReviews([]);
      setActiveTeacherReviewTargetId(null);
      return;
    }

    const teacherId = currentAccount?.teacher_id ?? null;

    if (!teacherId) {
      setTeacherReviews([]);
      setActiveTeacherReviewTargetId(null);
      return;
    }

    async function loadTeacherReviews() {
      setIsTeacherReviewsLoading(true);
      setActiveTeacherReviewTargetId(teacherId);

      try {
        const rows = await listTeacherReviews(teacherId, { limit: 20 });
        setTeacherReviews(rows);
      } catch (error) {
        setNotice({
          kind: "error",
          text: `Не вдалося завантажити відгуки: ${error.message}`,
        });
      } finally {
        setIsTeacherReviewsLoading(false);
      }
    }

    void loadTeacherReviews();
  }, [currentAccount?.teacher_id, role]);

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
      setTeacherAnalyticsPage(1);
      setDisciplineAnalyticsPage(1);
      setHasMoreTeacherAnalytics(false);
      setHasMoreDisciplineAnalytics(false);
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
      const teacherSkip =
        (teacherAnalyticsPage - 1) * ADMIN_ANALYTICS_PAGE_SIZE;
      const disciplineSkip =
        (disciplineAnalyticsPage - 1) * ADMIN_ANALYTICS_PAGE_SIZE;

      try {
        const [overview, teacherRows, disciplineRows] = await Promise.all([
          getOverviewAnalytics(analyticsQuery),
          listTeacherAnalytics({
            ...analyticsQuery,
            skip: teacherSkip,
            limit: ADMIN_ANALYTICS_PAGE_SIZE,
          }),
          listDisciplineAnalytics({
            ...analyticsQuery,
            skip: disciplineSkip,
            limit: ADMIN_ANALYTICS_PAGE_SIZE,
          }),
        ]);

        setOverviewAnalytics(overview);
        setTeacherAnalyticsRows(teacherRows);
        setDisciplineAnalyticsRows(disciplineRows);
        setHasMoreTeacherAnalytics(
          teacherRows.length === ADMIN_ANALYTICS_PAGE_SIZE,
        );
        setHasMoreDisciplineAnalytics(
          disciplineRows.length === ADMIN_ANALYTICS_PAGE_SIZE,
        );
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
    disciplineAnalyticsPage,
    role,
    teacherAnalyticsPage,
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

  async function refreshNotifications({ silent = false } = {}) {
    if (!currentAccount?.user_id) {
      setNotifications([]);
      return;
    }

    if (!silent) {
      setIsNotificationsLoading(true);
    }

    try {
      const rows = await listMyNotifications();
      setNotifications(rows);
    } catch (error) {
      if (!silent) {
        setNotice({
          kind: "error",
          text: `Не вдалося завантажити сповіщення: ${error.message}`,
        });
      }
    } finally {
      if (!silent) {
        setIsNotificationsLoading(false);
      }
    }
  }

  async function handleToggleNotifications() {
    const nextOpenState = !isNotificationsOpen;
    setIsNotificationsOpen(nextOpenState);
    setIsUserMenuOpen(false);

    if (nextOpenState) {
      await refreshNotifications();
    }
  }

  async function handleNotificationClick(notification) {
    if (notification.is_read) {
      return;
    }

    setNotificationActionId(notification.id);

    try {
      const updated = await markNotificationAsRead(notification.id);
      setNotifications((previous) =>
        previous.map((item) => (item.id === updated.id ? updated : item)),
      );
    } catch (error) {
      setNotice({
        kind: "error",
        text: `Не вдалося оновити сповіщення: ${error.message}`,
      });
    } finally {
      setNotificationActionId(null);
    }
  }

  async function handleClearNotificationsHistory() {
    if (!currentAccount?.user_id || notifications.length === 0) {
      return;
    }

    setIsNotificationsClearing(true);

    try {
      await clearMyNotifications();
      setNotifications([]);
      setNotice({ kind: "success", text: "Історію сповіщень очищено." });
    } catch (error) {
      setNotice({
        kind: "error",
        text: `Не вдалося очистити історію сповіщень: ${error.message}`,
      });
    } finally {
      setIsNotificationsClearing(false);
    }
  }

  function handleLogout() {
    clearAccessToken();
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setCurrentAccount(null);
    setIsUserMenuOpen(false);
    setIsNotificationsOpen(false);
    setNotifications([]);
    setIsNotificationsClearing(false);
    setProfileUpdateDraft(EMPTY_PROFILE_UPDATE_DRAFT);
    setReviewEditorBookingId(null);
    setReviewDraftByBookingId({});
    setTeacherDetailsModalContext(null);
    setTeacherDetailsModalReviews([]);
    setShowAllTeacherDetailsModalReviews(false);
    if (typeof window !== "undefined") {
      window.history.replaceState({}, "", "/");
    }
    setCurrentPath("/");
    setBookings([]);
    setTeacherSlots([]);
    setTeacherSlotBookingsBySlotId({});
    setExpandedTeacherSlotId(null);
    setActiveTeacherSlotsPage(1);
    setTeacherSlotHistoryPage(1);
    setUpcomingBookingsPage(1);
    setHistoryBookingsPage(1);
    setTeacherRegistrationForm(EMPTY_TEACHER_REGISTRATION);
    setStudentRegisterEmailError("");
    setTeacherRegistrationEmailError("");
    setProfileEmailError("");
    setAdminAnalyticsFilters(EMPTY_ADMIN_ANALYTICS_FILTERS);
    setOverviewAnalytics(null);
    setTeacherAnalyticsRows([]);
    setDisciplineAnalyticsRows([]);
    setTeacherAnalyticsPage(1);
    setDisciplineAnalyticsPage(1);
    setHasMoreTeacherAnalytics(false);
    setHasMoreDisciplineAnalytics(false);
    setNotice({ kind: "info", text: "Сесію завершено." });
  }

  function handleLoginDraftChange(event) {
    const { name, value } = event.target;
    setLoginDraft((previous) => ({ ...previous, [name]: value }));
  }

  function handleStudentRegisterChange(event) {
    const { name, value } = event.target;
    setStudentRegisterDraft((previous) => ({ ...previous, [name]: value }));

    if (name === "email") {
      setStudentRegisterEmailError(
        getEmailValidationMessage(value, { required: false }),
      );
    }
  }

  function handleStudentRegisterEmailBlur() {
    setStudentRegisterEmailError(
      getEmailValidationMessage(studentRegisterDraft.email, { required: true }),
    );
  }

  function validateStudentRegistrationDraft() {
    const username = studentRegisterDraft.username.trim();
    const password = studentRegisterDraft.password;
    const confirmPassword = studentRegisterDraft.confirmPassword;
    const fullName = studentRegisterDraft.fullName.trim();
    const email = studentRegisterDraft.email.trim();

    if (username.length < 3) {
      return "Username має містити щонайменше 3 символи.";
    }
    if (password.length < 6) {
      return "Password має містити щонайменше 6 символів.";
    }
    if (password !== confirmPassword) {
      return "Паролі не збігаються";
    }
    if (!fullName) {
      return "Вкажіть повне ім'я.";
    }
    const emailValidationMessage = getEmailValidationMessage(email, {
      required: true,
    });
    if (emailValidationMessage) {
      setStudentRegisterEmailError(emailValidationMessage);
      return emailValidationMessage;
    }
    setStudentRegisterEmailError("");
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

  async function openTeacherDetailsModal({
    teacherId,
    teacherName,
    cityName,
    disciplineName = null,
    startsAt = null,
    endsAt = null,
    description = null,
    averageRating = null,
    reviewsCount = 0,
    source = "teacher",
  }) {
    if (!teacherId) {
      return;
    }

    setTeacherDetailsModalContext({
      teacherId,
      teacherName,
      cityName,
      disciplineName,
      startsAt,
      endsAt,
      description,
      averageRating,
      reviewsCount,
      source,
    });
    setTeacherDetailsModalReviews([]);
    setShowAllTeacherDetailsModalReviews(false);
    setIsTeacherDetailsModalReviewsLoading(true);

    try {
      const rows = await listTeacherReviews(teacherId, { limit: 200 });
      setTeacherDetailsModalReviews(rows);
    } catch (error) {
      setNotice({
        kind: "error",
        text: `Не вдалося завантажити відгуки викладача: ${error.message}`,
      });
    } finally {
      setIsTeacherDetailsModalReviewsLoading(false);
    }
  }

  function closeTeacherDetailsModal() {
    setTeacherDetailsModalContext(null);
    setTeacherDetailsModalReviews([]);
    setShowAllTeacherDetailsModalReviews(false);
  }

  function handlePreviousStudentSlotsPage() {
    setStudentSlotsPage((previous) => Math.max(previous - 1, 1));
  }

  function handleNextStudentSlotsPage() {
    if (!hasMoreAvailableSlots) {
      return;
    }
    setStudentSlotsPage((previous) => previous + 1);
  }

  function handlePreviousStudentBookingsPage() {
    if (studentBookingTab === "upcoming") {
      setUpcomingBookingsPage((previous) => Math.max(previous - 1, 1));
      return;
    }

    setHistoryBookingsPage((previous) => Math.max(previous - 1, 1));
  }

  function handleNextStudentBookingsPage() {
    if (!hasMoreShownBookings) {
      return;
    }

    if (studentBookingTab === "upcoming") {
      setUpcomingBookingsPage((previous) => previous + 1);
      return;
    }

    setHistoryBookingsPage((previous) => previous + 1);
  }

  function handlePreviousActiveTeacherSlotsPage() {
    setActiveTeacherSlotsPage((previous) => Math.max(previous - 1, 1));
  }

  function handleNextActiveTeacherSlotsPage() {
    if (!hasMoreActiveTeacherSlots) {
      return;
    }

    setActiveTeacherSlotsPage((previous) => previous + 1);
  }

  function handlePreviousTeacherSlotHistoryPage() {
    setTeacherSlotHistoryPage((previous) => Math.max(previous - 1, 1));
  }

  function handleNextTeacherSlotHistoryPage() {
    if (!hasMoreTeacherSlotHistory) {
      return;
    }

    setTeacherSlotHistoryPage((previous) => previous + 1);
  }

  function handlePreviousTeacherAnalyticsPage() {
    setTeacherAnalyticsPage((previous) => Math.max(previous - 1, 1));
  }

  function handleNextTeacherAnalyticsPage() {
    if (!hasMoreTeacherAnalytics) {
      return;
    }

    setTeacherAnalyticsPage((previous) => previous + 1);
  }

  function handlePreviousDisciplineAnalyticsPage() {
    setDisciplineAnalyticsPage((previous) => Math.max(previous - 1, 1));
  }

  function handleNextDisciplineAnalyticsPage() {
    if (!hasMoreDisciplineAnalytics) {
      return;
    }

    setDisciplineAnalyticsPage((previous) => previous + 1);
  }

  function toggleAvailableSlotDescription(slotId) {
    setExpandedAvailableSlotDescriptions((previous) => ({
      ...previous,
      [slotId]: !previous[slotId],
    }));
  }

  function toggleBookingDescription(bookingId) {
    setExpandedBookingDescriptions((previous) => ({
      ...previous,
      [bookingId]: !previous[bookingId],
    }));
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

  function handleTeacherRegistrationFieldChange(event) {
    const { name, value } = event.target;
    setTeacherRegistrationForm((previous) => ({
      ...previous,
      [name]: value,
    }));

    if (name === "email") {
      setTeacherRegistrationEmailError(
        getEmailValidationMessage(value, { required: false }),
      );
    }
  }

  function handleTeacherRegistrationEmailBlur() {
    setTeacherRegistrationEmailError(
      getEmailValidationMessage(teacherRegistrationForm.email, {
        required: true,
      }),
    );
  }

  function handleAdminAnalyticsFilterChange(event) {
    const { name, value } = event.target;
    setTeacherAnalyticsPage(1);
    setDisciplineAnalyticsPage(1);
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

    if (name === "email") {
      setProfileEmailError(
        getEmailValidationMessage(value, { required: false }),
      );
    }
  }

  function handleProfileEmailBlur() {
    setProfileEmailError(
      getEmailValidationMessage(profileUpdateDraft.email, { required: true }),
    );
  }

  async function handleTeacherEmailUpdate() {
    if (!currentAccount || role !== "teacher") {
      return;
    }

    const email = profileUpdateDraft.email.trim().toLowerCase();
    const emailValidationMessage = getEmailValidationMessage(email, {
      required: true,
    });
    setProfileEmailError(emailValidationMessage);
    if (emailValidationMessage) {
      setNotice({
        kind: "error",
        text: emailValidationMessage,
      });
      return;
    }

    if (email === (currentAccount.email ?? "")) {
      setNotice({
        kind: "warning",
        text: "Email не змінився.",
      });
      return;
    }

    setIsProfileSubmitting(true);

    try {
      const updatedAccount = await updateCurrentAccount({ email });
      setCurrentAccount(updatedAccount);
      setProfileUpdateDraft((previous) => ({
        ...previous,
        email: updatedAccount.email ?? "",
      }));
      setProfileEmailError("");
      setNotice({ kind: "success", text: "Email оновлено." });
    } catch (error) {
      setNotice({
        kind: "error",
        text: `Не вдалося оновити email: ${error.message}`,
      });
    } finally {
      setIsProfileSubmitting(false);
    }
  }

  async function handleProfileUpdate(event) {
    event.preventDefault();

    if (!currentAccount) {
      return;
    }

    const username = profileUpdateDraft.username.trim().toLowerCase();
    const fullName = profileUpdateDraft.fullName.trim();
    const email = profileUpdateDraft.email.trim().toLowerCase();

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

    if (!username) {
      setNotice({
        kind: "warning",
        text: "Username не може бути порожнім.",
      });
      return;
    }

    if (canEditProfileFullName && !fullName) {
      setNotice({
        kind: "warning",
        text: "ПІБ не може бути порожнім.",
      });
      return;
    }

    const usernameChanged = username !== currentAccount.username;
    const fullNameChanged =
      canEditProfileFullName && fullName !== (currentAccount.full_name ?? "");
    const emailChanged =
      canEditProfileEmail && email !== (currentAccount.email ?? "");

    if (canEditProfileEmail && emailChanged) {
      const emailValidationMessage = getEmailValidationMessage(email, {
        required: true,
      });
      setProfileEmailError(emailValidationMessage);
      if (emailValidationMessage) {
        setNotice({
          kind: "error",
          text: emailValidationMessage,
        });
        return;
      }
    } else if (canEditProfileEmail) {
      setProfileEmailError("");
    }

    const cityChanged =
      canEditProfileCity &&
      profileUpdateDraft.cityId &&
      String(currentAccount.city_id ?? "") !==
        String(profileUpdateDraft.cityId);
    const wantsPasswordUpdate = Boolean(currentPassword && newPassword);

    if (!cityChanged && !wantsPasswordUpdate) {
      const hasProfileFieldsChanged =
        usernameChanged || fullNameChanged || emailChanged;

      if (hasProfileFieldsChanged) {
        // Continue to submission below when profile fields changed.
      } else {
        setNotice({
          kind: "warning",
          text:
            role === "admin"
              ? "Змініть username або заповніть обидва поля пароля."
              : "Немає змін для оновлення профілю.",
        });
        return;
      }
    }

    const hasAnyChange =
      usernameChanged ||
      fullNameChanged ||
      emailChanged ||
      cityChanged ||
      wantsPasswordUpdate;

    if (!hasAnyChange) {
      setNotice({
        kind: "warning",
        text: "Немає змін для оновлення профілю.",
      });
      return;
    }

    setIsProfileSubmitting(true);

    try {
      const updatedAccount = await updateCurrentAccount({
        username: usernameChanged ? username : undefined,
        fullName: fullNameChanged ? fullName : undefined,
        email: emailChanged ? email : undefined,
        cityId: cityChanged ? profileUpdateDraft.cityId : undefined,
        currentPassword: currentPassword || undefined,
        newPassword: newPassword || undefined,
      });

      setCurrentAccount(updatedAccount);
      setProfileUpdateDraft({
        username: updatedAccount.username ?? "",
        fullName: updatedAccount.full_name ?? "",
        email: updatedAccount.email ?? "",
        cityId:
          updatedAccount.city_id != null ? String(updatedAccount.city_id) : "",
        currentPassword: "",
        newPassword: "",
      });
      setProfileEmailError("");

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
        bookingId: booking.booking_id,
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

      if (activeTeacherReviewTargetId) {
        const loadedReviews = await listTeacherReviews(
          activeTeacherReviewTargetId,
          { limit: 20 },
        );
        setTeacherReviews(loadedReviews);
      }

      if (teacherDetailsModalContext?.teacherId === booking.teacher_id) {
        const loadedModalReviews = await listTeacherReviews(
          booking.teacher_id,
          {
            limit: 200,
          },
        );
        setTeacherDetailsModalReviews(loadedModalReviews);
      }

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
      setNotice({
        kind:
          validationError === "Паролі не збігаються" ||
          validationError === EMAIL_VALIDATION_MESSAGE
            ? "error"
            : "warning",
        text: validationError,
      });
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
      setStudentRegisterEmailError("");
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

      const skip = (studentSlotsPage - 1) * STUDENT_SLOTS_PAGE_SIZE;
      const baseQuery = {
        cityId: studentFilters.cityId || undefined,
        disciplineId: studentFilters.disciplineId || undefined,
        teacherId: studentFilters.teacherId || undefined,
      };

      const [slots, nextPageProbe, loadedBookings] = await Promise.all([
        listAvailableSlots({
          ...baseQuery,
          skip,
          limit: STUDENT_SLOTS_PAGE_SIZE,
        }),
        listAvailableSlots({
          ...baseQuery,
          skip: skip + STUDENT_SLOTS_PAGE_SIZE,
          limit: 1,
        }),
        listBookings(),
      ]);

      if (studentSlotsPage > 1 && slots.length === 0) {
        setStudentSlotsPage((previous) => Math.max(previous - 1, 1));
      } else {
        setAvailableSlots(slots);
        setHasMoreAvailableSlots(nextPageProbe.length > 0);
        setExpandedAvailableSlotDescriptions({});
      }
      setBookings(loadedBookings);
      setExpandedBookingDescriptions({});
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

      const skip = (studentSlotsPage - 1) * STUDENT_SLOTS_PAGE_SIZE;
      const baseQuery = {
        cityId: studentFilters.cityId || undefined,
        disciplineId: studentFilters.disciplineId || undefined,
        teacherId: studentFilters.teacherId || undefined,
      };

      const [slots, nextPageProbe, loadedBookings] = await Promise.all([
        listAvailableSlots({
          ...baseQuery,
          skip,
          limit: STUDENT_SLOTS_PAGE_SIZE,
        }),
        listAvailableSlots({
          ...baseQuery,
          skip: skip + STUDENT_SLOTS_PAGE_SIZE,
          limit: 1,
        }),
        listBookings(),
      ]);

      if (studentSlotsPage > 1 && slots.length === 0) {
        setStudentSlotsPage((previous) => Math.max(previous - 1, 1));
      } else {
        setAvailableSlots(slots);
        setHasMoreAvailableSlots(nextPageProbe.length > 0);
        setExpandedAvailableSlotDescriptions({});
      }
      setBookings(loadedBookings);
      setExpandedBookingDescriptions({});
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
        description: teacherSlotForm.description,
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
      description: slot.description ?? "",
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
        description: editingSlotForm.description,
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
      setNotice({
        kind: "success",
        text: "Слот переміщено в історію, активні записи автоматично скасовано.",
      });
    } catch (error) {
      setNotice({
        kind: "error",
        text: `Не вдалося видалити слот: ${error.message}`,
      });
    } finally {
      setSlotActionInProgressId(null);
    }
  }

  async function handleCompleteTeacherSlot(slotId) {
    setSlotActionInProgressId(slotId);

    try {
      await completeTeacherSlot(slotId);
      const loadedSlots = await listTeacherSlots();
      setTeacherSlots(loadedSlots);

      if (expandedTeacherSlotId === slotId) {
        const slotBookings = await listTeacherSlotBookings(slotId);
        setTeacherSlotBookingsBySlotId((previous) => ({
          ...previous,
          [slotId]: slotBookings,
        }));
      }

      setNotice({
        kind: "success",
        text: "Пару завершено, слот переміщено в історію.",
      });
    } catch (error) {
      setNotice({
        kind: "error",
        text: `Не вдалося завершити пару: ${error.message}`,
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

  async function handleTeacherCompleteAllBookings(slotId) {
    const actionKey = `${slotId}:all:complete`;
    setTeacherBookingActionKey(actionKey);

    try {
      const result = await completeAllTeacherSlotBookings(slotId);
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
        text: `Завершено записів: ${result.updated_bookings}.`,
      });
    } catch (error) {
      setNotice({
        kind: "error",
        text: `Не вдалося завершити всі записи: ${error.message}`,
      });
    } finally {
      setTeacherBookingActionKey(null);
    }
  }

  async function handleCreateTeacherAccount(event) {
    event.preventDefault();

    const username = teacherRegistrationForm.username.trim().toLowerCase();
    const fullName = teacherRegistrationForm.fullName.trim();
    const email = teacherRegistrationForm.email.trim().toLowerCase();
    const password = teacherRegistrationForm.password;
    const confirmPassword = teacherRegistrationForm.confirmPassword;
    const cityId = teacherRegistrationForm.cityId;

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

    if (password !== confirmPassword) {
      setNotice({
        kind: "error",
        text: "Паролі не збігаються",
      });
      return;
    }

    if (!fullName) {
      setNotice({
        kind: "warning",
        text: "Вкажіть ПІБ викладача.",
      });
      return;
    }

    const emailValidationMessage = getEmailValidationMessage(email, {
      required: true,
    });
    setTeacherRegistrationEmailError(emailValidationMessage);
    if (emailValidationMessage) {
      setNotice({
        kind: "error",
        text: emailValidationMessage,
      });
      return;
    }

    if (!cityId) {
      setNotice({
        kind: "warning",
        text: "Оберіть місто викладача.",
      });
      return;
    }

    setIsTeacherRegistrationSubmitting(true);
    let createdTeacherId = null;

    try {
      const teacher = await createTeacher({
        fullName,
        cityId,
      });
      createdTeacherId = teacher.id;

      await createTeacherAccount({
        username,
        password,
        fullName,
        email,
        teacherId: createdTeacherId,
      });

      const loadedTeachers = await listTeachers();
      setTeacherDirectory(loadedTeachers);
      setTeachers(loadedTeachers);

      if (adminAccountsSkip !== 0) {
        setAdminAccountsSkip(0);
      } else {
        await loadAdminAccountsPage(0);
      }

      setTeacherRegistrationForm(EMPTY_TEACHER_REGISTRATION);
      setTeacherRegistrationEmailError("");
      setNotice({ kind: "success", text: "Викладача успішно створено." });
    } catch (error) {
      if (createdTeacherId != null) {
        try {
          const loadedTeachers = await listTeachers();
          setTeacherDirectory(loadedTeachers);
          setTeachers(loadedTeachers);
        } catch {
          // Keep the primary registration error if directory refresh fails.
        }

        setNotice({
          kind: "error",
          text: `Профіль викладача створено, але акаунт доступу не створено: ${error.message}`,
        });
        return;
      }

      setNotice({
        kind: "error",
        text: `Не вдалося створити викладача: ${error.message}`,
      });
    } finally {
      setIsTeacherRegistrationSubmitting(false);
    }
  }

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

          <div className="top-nav-actions">
            <div className="notifications-wrap" ref={notificationsWrapRef}>
              <button
                type="button"
                className="icon-button bell-button"
                aria-haspopup="menu"
                aria-expanded={isNotificationsOpen}
                aria-controls="notifications-dropdown"
                onClick={handleToggleNotifications}
              >
                <span aria-hidden="true">🔔</span>
                {hasUnreadNotifications ? (
                  <span className="notification-badge" aria-hidden="true" />
                ) : null}
              </button>

              {isNotificationsOpen ? (
                <div
                  className="notifications-dropdown"
                  id="notifications-dropdown"
                >
                  <div className="notifications-header-row">
                    <p className="notifications-title">Сповіщення</p>
                    <button
                      type="button"
                      className="ghost notification-clear-button"
                      onClick={handleClearNotificationsHistory}
                      disabled={
                        isNotificationsLoading ||
                        isNotificationsClearing ||
                        notifications.length === 0
                      }
                    >
                      {isNotificationsClearing
                        ? "Очищення..."
                        : "Очистити історію"}
                    </button>
                  </div>

                  {isNotificationsLoading ? (
                    <p className="meta-line">Завантаження...</p>
                  ) : notifications.length === 0 ? (
                    <p className="meta-line">Поки що сповіщень немає.</p>
                  ) : (
                    <ul className="notifications-list">
                      {notifications.map((notification) => (
                        <li key={notification.id}>
                          <button
                            type="button"
                            className={`notification-item ${
                              notification.is_read ? "" : "is-unread"
                            }`}
                            onClick={() =>
                              handleNotificationClick(notification)
                            }
                            disabled={notificationActionId === notification.id}
                          >
                            <span className="notification-item-title">
                              {notification.title}
                            </span>
                            <span className="notification-item-message">
                              {notification.message}
                            </span>
                            <span className="notification-item-time">
                              {formatDateTime(notification.created_at)}
                            </span>
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ) : null}
            </div>

            <div className="top-nav-menu-wrap" ref={userMenuWrapRef}>
              <button
                type="button"
                className="avatar-button"
                aria-haspopup="menu"
                aria-expanded={isUserMenuOpen}
                aria-controls="user-menu-dropdown"
                onClick={() => {
                  setIsNotificationsOpen(false);
                  setIsUserMenuOpen((previous) => !previous);
                }}
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
                  <button
                    type="button"
                    className="danger"
                    onClick={handleLogout}
                  >
                    Вийти
                  </button>
                </div>
              ) : null}
            </div>
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

            <p className="hint-text">Demo: admin/admin12345</p>
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
                Підтвердіть Password
                <input
                  name="confirmPassword"
                  type="password"
                  value={studentRegisterDraft.confirmPassword}
                  onChange={handleStudentRegisterChange}
                  placeholder="Повторіть пароль"
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
                  onBlur={handleStudentRegisterEmailBlur}
                  placeholder="student@example.com"
                />
              </label>

              {studentRegisterEmailError ? (
                <p className="field-error">{studentRegisterEmailError}</p>
              ) : null}

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
        <section className="profile-page-stack">
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

          {profileFocusSection === "profile" ? (
            <article
              className="panel reveal"
              style={{ animationDelay: "220ms" }}
            >
              <h2>Інформація профілю</h2>
              <p className="meta-line">
                У цій вкладці відображаються ваші поточні дані акаунта.
              </p>
              <p className="meta-line">
                Для оновлення даних відкрийте вкладку "Налаштування".
              </p>
              <p className="hint-text">
                Порада: зміни username і пароля застосовуються одразу після
                збереження.
              </p>
            </article>
          ) : (
            <article
              id="profile-settings-card"
              className="panel reveal"
              style={{ animationDelay: "220ms" }}
            >
              <h2>Налаштування облікового запису</h2>
              <form className="profile-form" onSubmit={handleProfileUpdate}>
                <label>
                  Username
                  <input
                    name="username"
                    value={profileUpdateDraft.username}
                    onChange={handleProfileUpdateDraftChange}
                    placeholder="Ваш username"
                    autoComplete="username"
                  />
                </label>

                {canEditProfileFullName ? (
                  <label>
                    ПІБ
                    <input
                      name="fullName"
                      value={profileUpdateDraft.fullName}
                      onChange={handleProfileUpdateDraftChange}
                      placeholder="Ваше повне ім'я"
                    />
                  </label>
                ) : null}

                {canEditProfileEmail ? (
                  <>
                    <label>
                      Email
                      <input
                        name="email"
                        type="email"
                        value={profileUpdateDraft.email}
                        onChange={handleProfileUpdateDraftChange}
                        onBlur={handleProfileEmailBlur}
                        placeholder="you@example.com"
                        autoComplete="email"
                      />
                    </label>

                    {profileEmailError ? (
                      <p className="field-error">{profileEmailError}</p>
                    ) : null}
                  </>
                ) : null}

                {role === "teacher" ? (
                  <button
                    type="button"
                    className="ghost"
                    onClick={handleTeacherEmailUpdate}
                    disabled={isProfileSubmitting}
                  >
                    {isProfileSubmitting ? "Оновлюю..." : "Оновити Email"}
                  </button>
                ) : null}

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
                    Для ролі admin місто, ПІБ та email не редагуються.
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
          )}
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

              <div className="filters-grid slot-filters">
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
                        {teacher.full_name} ·{" "}
                        {formatTeacherRatingSummary(
                          teacher.average_rating,
                          teacher.reviews_count,
                        )}
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
              <h2>Викладачі у фільтрі</h2>

              {teachers.length === 0 ? (
                <p className="empty-state">
                  За поточними фільтрами викладачів не знайдено.
                </p>
              ) : (
                <div className="analytics-list teacher-preview-list">
                  {teachers.slice(0, 8).map((teacher) => (
                    <article
                      key={teacher.id}
                      className="analytics-item teacher-preview-item"
                    >
                      <p>
                        <strong>{teacher.full_name}</strong>
                      </p>
                      <p className="meta-line">
                        {cityNameById.get(teacher.city_id) ||
                          "Місто не вказано"}
                      </p>
                      <p className="meta-line teacher-rating-line">
                        {formatTeacherRatingSummary(
                          teacher.average_rating,
                          teacher.reviews_count,
                        )}
                      </p>
                      <button
                        type="button"
                        className="ghost"
                        onClick={() =>
                          void openTeacherDetailsModal({
                            teacherId: teacher.id,
                            teacherName: teacher.full_name,
                            cityName: cityNameById.get(teacher.city_id) || null,
                            averageRating: teacher.average_rating,
                            reviewsCount: teacher.reviews_count,
                            source: "teacher",
                          })
                        }
                      >
                        Профіль і відгуки
                      </button>
                    </article>
                  ))}
                </div>
              )}

              <div className="inline-actions analytics-pagination">
                <button
                  type="button"
                  className="ghost"
                  onClick={handlePreviousTeacherAnalyticsPage}
                  disabled={
                    isAdminAnalyticsLoading || teacherAnalyticsPage === 1
                  }
                >
                  Назад
                </button>
                <button
                  type="button"
                  className="ghost"
                  onClick={handleNextTeacherAnalyticsPage}
                  disabled={isAdminAnalyticsLoading || !hasMoreTeacherAnalytics}
                >
                  Далі
                </button>
              </div>
            </article>
          </section>

          {teacherDetailsModalContext ? (
            <div className="modal-overlay" role="dialog" aria-modal="true">
              <div className="modal-card">
                <div className="panel-header-row">
                  <h2>
                    {teacherDetailsModalContext.source === "slot"
                      ? "Деталі слота"
                      : "Профіль викладача"}
                  </h2>
                  <button
                    type="button"
                    className="ghost"
                    onClick={closeTeacherDetailsModal}
                  >
                    Закрити
                  </button>
                </div>

                <div className="modal-summary-grid">
                  <p className="meta-line">
                    Викладач:{" "}
                    <strong>{teacherDetailsModalContext.teacherName}</strong>
                  </p>
                  <p className="meta-line">
                    Рейтинг:{" "}
                    {formatTeacherRatingSummary(
                      teacherDetailsModalContext.averageRating,
                      teacherDetailsModalContext.reviewsCount,
                    )}
                  </p>
                  <p className="meta-line">
                    Місто: {teacherDetailsModalContext.cityName || "Не вказано"}
                  </p>

                  {teacherDetailsModalContext.source === "slot" ? (
                    <>
                      <p className="meta-line">
                        Дисципліна:{" "}
                        {teacherDetailsModalContext.disciplineName ||
                          "Не вказано"}
                      </p>
                      <p className="meta-line">
                        Час:{" "}
                        {formatDateTimeRange(
                          teacherDetailsModalContext.startsAt,
                          teacherDetailsModalContext.endsAt,
                        )}
                      </p>
                      <p className="meta-line">
                        Опис:{" "}
                        {teacherDetailsModalContext.description || "Не вказано"}
                      </p>
                    </>
                  ) : null}
                </div>

                <h3>Відгуки студентів</h3>

                {isTeacherDetailsModalReviewsLoading ? (
                  <p className="meta-line">Завантажую відгуки...</p>
                ) : teacherDetailsModalReviews.length === 0 ? (
                  <p className="empty-state">
                    Для цього викладача поки немає відгуків.
                  </p>
                ) : (
                  <>
                    <div className="analytics-list modal-reviews-list">
                      {displayedTeacherDetailsModalReviews.map((review) => (
                        <article
                          key={review.review_id}
                          className="analytics-item review-item"
                        >
                          <p>
                            <strong>{review.student_name}</strong> ·{" "}
                            {getReviewStars(review.rating)} ({review.rating}/5)
                          </p>
                          <p className="meta-line">
                            {formatDateTime(review.created_at)}
                          </p>
                          <p className="meta-line">
                            {review.comment || "Без текстового коментаря."}
                          </p>
                        </article>
                      ))}
                    </div>

                    {hasHiddenTeacherDetailsModalReviews ? (
                      <div className="inline-actions">
                        <button
                          type="button"
                          className="ghost"
                          onClick={() =>
                            setShowAllTeacherDetailsModalReviews(
                              (previous) => !previous,
                            )
                          }
                        >
                          {showAllTeacherDetailsModalReviews
                            ? "Показати останні 5"
                            : `Показати всі (${teacherDetailsModalReviews.length})`}
                        </button>
                      </div>
                    ) : null}
                  </>
                )}
              </div>
            </div>
          ) : null}

          <section className="panel reveal" style={{ animationDelay: "320ms" }}>
            <div className="panel-header-row">
              <h2>Вільні слоти</h2>
              <span className="badge">
                {isSlotsLoading
                  ? "Оновлення..."
                  : `Сторінка ${studentSlotsPage} · ${availableSlots.length} слот(ів)`}
              </span>
            </div>

            {availableSlots.length === 0 && !isSlotsLoading ? (
              <p className="empty-state">
                Слоти за поточними фільтрами відсутні.
              </p>
            ) : (
              <>
                <div className="slot-grid">
                  {availableSlots.map((slot, index) => {
                    const hasActiveBooking = activeStudentBookingSlotIds.has(
                      slot.slot_id,
                    );
                    const description = slot.description?.trim() ?? "";
                    const isDescriptionLong = description.length > 160;
                    const isDescriptionExpanded = Boolean(
                      expandedAvailableSlotDescriptions[slot.slot_id],
                    );
                    const shownDescription =
                      isDescriptionLong && !isDescriptionExpanded
                        ? `${description.slice(0, 160)}...`
                        : description;

                    return (
                      <article
                        className="slot-card"
                        key={slot.slot_id}
                        style={{ animationDelay: `${index * 70 + 180}ms` }}
                      >
                        <p className="slot-topic">{slot.discipline_name}</p>
                        <div className="slot-title-row">
                          <h3>{slot.teacher_name}</h3>
                          <span className="slot-rating-chip">
                            {formatTeacherRatingSummary(
                              slot.average_rating,
                              slot.reviews_count,
                            )}
                          </span>
                        </div>
                        <p className="slot-meta">{slot.city_name}</p>
                        <p className="slot-time">
                          {formatDateTimeRange(slot.starts_at, slot.ends_at)}
                        </p>
                        <p className="slot-capacity">
                          Місця: {slot.available_seats}/{slot.capacity}
                        </p>

                        {description ? (
                          <>
                            <p className="slot-description">
                              {shownDescription}
                            </p>
                            {isDescriptionLong ? (
                              <button
                                type="button"
                                className="ghost"
                                onClick={() =>
                                  toggleAvailableSlotDescription(slot.slot_id)
                                }
                              >
                                {isDescriptionExpanded
                                  ? "Сховати опис"
                                  : "Читати опис"}
                              </button>
                            ) : null}
                          </>
                        ) : (
                          <p className="slot-meta">Опис не вказано.</p>
                        )}

                        <div className="inline-actions">
                          <button
                            type="button"
                            className="ghost"
                            onClick={() =>
                              void openTeacherDetailsModal({
                                teacherId: slot.teacher_id,
                                teacherName: slot.teacher_name,
                                cityName: slot.city_name,
                                disciplineName: slot.discipline_name,
                                startsAt: slot.starts_at,
                                endsAt: slot.ends_at,
                                description: slot.description,
                                averageRating: slot.average_rating,
                                reviewsCount: slot.reviews_count,
                                source: "slot",
                              })
                            }
                          >
                            Деталі
                          </button>

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
                        </div>
                      </article>
                    );
                  })}
                </div>

                <div className="inline-actions pagination-controls">
                  <button
                    type="button"
                    className="ghost"
                    onClick={handlePreviousStudentSlotsPage}
                    disabled={studentSlotsPage === 1 || isSlotsLoading}
                  >
                    Назад
                  </button>
                  <button
                    type="button"
                    className="ghost"
                    onClick={handleNextStudentSlotsPage}
                    disabled={!hasMoreAvailableSlots || isSlotsLoading}
                  >
                    Далі
                  </button>
                </div>
              </>
            )}
          </section>

          <section className="panel reveal" style={{ animationDelay: "420ms" }}>
            <div className="panel-header-row">
              <h2>Мої бронювання</h2>
              <span className="badge">
                {isBookingsLoading
                  ? "Оновлення..."
                  : `Сторінка ${currentStudentBookingsPage} · ${shownBookings.length} запис(ів)`}
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
              <>
                <div className="booking-list">
                  {shownBookings.map((booking, index) => {
                    const description = booking.description?.trim() ?? "";
                    const isDescriptionLong = description.length > 160;
                    const isDescriptionExpanded = Boolean(
                      expandedBookingDescriptions[booking.booking_id],
                    );
                    const shownDescription =
                      isDescriptionLong && !isDescriptionExpanded
                        ? `${description.slice(0, 160)}...`
                        : description;

                    return (
                      <article
                        className="booking-item"
                        key={booking.booking_id}
                        style={{ animationDelay: `${index * 70 + 220}ms` }}
                      >
                        <div>
                          <p className="slot-topic">
                            {booking.discipline_name}
                          </p>
                          <h3>{booking.teacher_name}</h3>
                          <p className="slot-meta">{booking.city_name}</p>
                          <p className="slot-time">
                            {formatDateTimeRange(
                              booking.starts_at,
                              booking.ends_at,
                            )}
                          </p>
                          {description ? (
                            <>
                              <p className="slot-description">
                                {shownDescription}
                              </p>
                              {isDescriptionLong ? (
                                <button
                                  type="button"
                                  className="ghost"
                                  onClick={() =>
                                    toggleBookingDescription(booking.booking_id)
                                  }
                                >
                                  {isDescriptionExpanded
                                    ? "Сховати опис"
                                    : "Читати опис"}
                                </button>
                              ) : null}
                            </>
                          ) : (
                            <p className="slot-meta">Опис не вказано.</p>
                          )}
                          <p className="slot-meta">
                            Статус:{" "}
                            {String(booking.status ?? "active").toUpperCase()}
                          </p>

                          {booking.status === "completed" &&
                          booking.has_review ? (
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
                                      reviewDraftByBookingId[
                                        booking.booking_id
                                      ] ?? EMPTY_REVIEW_DRAFT
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
                                      reviewDraftByBookingId[
                                        booking.booking_id
                                      ] ?? EMPTY_REVIEW_DRAFT
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
                                    reviewSubmittingBookingId ===
                                    booking.booking_id
                                  }
                                >
                                  {reviewSubmittingBookingId ===
                                  booking.booking_id
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
                              cancelInProgressBookingId ===
                                booking.booking_id ||
                              booking.status !== "active"
                            }
                          >
                            {booking.status !== "active"
                              ? "Недоступно"
                              : cancelInProgressBookingId === booking.booking_id
                                ? "Скасовую..."
                                : "Скасувати"}
                          </button>

                          {booking.status === "completed" &&
                          !booking.has_review ? (
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
                    );
                  })}
                </div>

                <div className="inline-actions pagination-controls">
                  <button
                    type="button"
                    className="ghost"
                    onClick={handlePreviousStudentBookingsPage}
                    disabled={
                      currentStudentBookingsPage === 1 || isBookingsLoading
                    }
                  >
                    Назад
                  </button>
                  <button
                    type="button"
                    className="ghost"
                    onClick={handleNextStudentBookingsPage}
                    disabled={!hasMoreShownBookings || isBookingsLoading}
                  >
                    Далі
                  </button>
                </div>
              </>
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

              <label className="span-all-columns">
                Опис заняття (необов'язково)
                <textarea
                  name="description"
                  value={teacherSlotForm.description}
                  onChange={handleTeacherSlotFormChange}
                  placeholder="Наприклад: теми заняття, домашнє завдання, посилання на матеріали"
                  rows={3}
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

            {isTeacherSlotsLoading ? (
              <p className="meta-line">Завантажую слоти...</p>
            ) : teacherSlots.length === 0 ? (
              <p className="empty-state">Поки що немає створених слотів.</p>
            ) : (
              <div className="slot-section-stack">
                <div className="slot-section-block">
                  <div className="panel-header-row slot-subheader-row">
                    <h3>Активні слоти</h3>
                    <span className="badge">
                      Сторінка {activeTeacherSlotsPage} ·{" "}
                      {activeTeacherSlots.length}
                    </span>
                  </div>

                  {activeTeacherSlots.length === 0 ? (
                    <p className="empty-state">
                      Немає активних слотів, що ще не завершилися за часом.
                    </p>
                  ) : (
                    <>
                      <div className="teacher-slot-grid">
                        {paginatedActiveTeacherSlots.map((slot, index) => (
                          <article
                            key={slot.slot_id}
                            className="slot-card"
                            style={{ animationDelay: `${index * 70 + 180}ms` }}
                          >
                            <p className="slot-topic">{slot.discipline_name}</p>
                            <h3>
                              {formatDateTimeRange(
                                slot.starts_at,
                                slot.ends_at,
                              )}
                            </h3>
                            <p className="slot-meta">
                              Місць: {slot.available_seats}/{slot.capacity} ·
                              Заброньовано: {slot.reserved_seats}
                            </p>
                            <p className="slot-meta">Статус: Активний</p>

                            <div className="inline-actions">
                              <button
                                type="button"
                                className="ghost"
                                onClick={() =>
                                  void handleToggleTeacherBookings(slot.slot_id)
                                }
                                disabled={
                                  teacherBookingsLoadingSlotId === slot.slot_id
                                }
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
                                onClick={() =>
                                  void handleCompleteTeacherSlot(slot.slot_id)
                                }
                                disabled={
                                  slotActionInProgressId === slot.slot_id
                                }
                              >
                                Завершити пару
                              </button>
                              <button
                                type="button"
                                className="danger"
                                onClick={() =>
                                  void handleDeleteTeacherSlot(slot.slot_id)
                                }
                                disabled={
                                  slotActionInProgressId === slot.slot_id
                                }
                              >
                                Видалити
                              </button>
                            </div>
                          </article>
                        ))}
                      </div>

                      <div className="inline-actions pagination-controls">
                        <button
                          type="button"
                          className="ghost"
                          onClick={handlePreviousActiveTeacherSlotsPage}
                          disabled={
                            activeTeacherSlotsPage === 1 ||
                            isTeacherSlotsLoading
                          }
                        >
                          Назад
                        </button>
                        <button
                          type="button"
                          className="ghost"
                          onClick={handleNextActiveTeacherSlotsPage}
                          disabled={
                            !hasMoreActiveTeacherSlots || isTeacherSlotsLoading
                          }
                        >
                          Далі
                        </button>
                      </div>
                    </>
                  )}
                </div>

                <div className="slot-section-block">
                  <div className="panel-header-row slot-subheader-row">
                    <h3>Історія / Неактивні</h3>
                    <span className="badge">
                      Сторінка {teacherSlotHistoryPage} ·{" "}
                      {teacherSlotHistory.length}
                    </span>
                  </div>

                  {teacherSlotHistory.length === 0 ? (
                    <p className="empty-state">Історія слотів поки порожня.</p>
                  ) : (
                    <>
                      <div className="teacher-slot-grid">
                        {paginatedTeacherSlotHistory.map((slot, index) => {
                          const endsAtMs = Date.parse(slot.ends_at);
                          const hasEnded =
                            !Number.isFinite(endsAtMs) ||
                            endsAtMs <= Date.now();
                          const canActivate =
                            !slot.is_active &&
                            Number.isFinite(endsAtMs) &&
                            endsAtMs > Date.now();
                          const historyStatusLabel = hasEnded
                            ? "Завершений"
                            : "Неактивний";

                          return (
                            <article
                              key={slot.slot_id}
                              className="slot-card"
                              style={{
                                animationDelay: `${index * 70 + 220}ms`,
                              }}
                            >
                              <p className="slot-topic">
                                {slot.discipline_name}
                              </p>
                              <h3>
                                {formatDateTimeRange(
                                  slot.starts_at,
                                  slot.ends_at,
                                )}
                              </h3>
                              <p className="slot-meta">
                                Місць: {slot.available_seats}/{slot.capacity} ·
                                Заброньовано: {slot.reserved_seats}
                              </p>
                              <p className="slot-meta">
                                Статус: {historyStatusLabel}
                              </p>

                              <div className="inline-actions">
                                <button
                                  type="button"
                                  className="ghost"
                                  onClick={() =>
                                    void handleToggleTeacherBookings(
                                      slot.slot_id,
                                    )
                                  }
                                  disabled={
                                    teacherBookingsLoadingSlotId ===
                                    slot.slot_id
                                  }
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
                                {canActivate ? (
                                  <button
                                    type="button"
                                    className="ghost"
                                    onClick={() =>
                                      void handleToggleTeacherSlotActive(slot)
                                    }
                                    disabled={
                                      slotActionInProgressId === slot.slot_id
                                    }
                                  >
                                    Активувати
                                  </button>
                                ) : null}
                              </div>
                            </article>
                          );
                        })}
                      </div>

                      <div className="inline-actions pagination-controls">
                        <button
                          type="button"
                          className="ghost"
                          onClick={handlePreviousTeacherSlotHistoryPage}
                          disabled={
                            teacherSlotHistoryPage === 1 ||
                            isTeacherSlotsLoading
                          }
                        >
                          Назад
                        </button>
                        <button
                          type="button"
                          className="ghost"
                          onClick={handleNextTeacherSlotHistoryPage}
                          disabled={
                            !hasMoreTeacherSlotHistory || isTeacherSlotsLoading
                          }
                        >
                          Далі
                        </button>
                      </div>
                    </>
                  )}
                </div>
              </div>
            )}
          </section>

          <section className="panel reveal" style={{ animationDelay: "350ms" }}>
            <div className="panel-header-row">
              <h2>Відгуки студентів</h2>
              <span className="badge">
                {isTeacherReviewsLoading
                  ? "Оновлення..."
                  : `Відгуків: ${teacherReviews.length}`}
              </span>
            </div>

            {isTeacherReviewsLoading ? (
              <p className="meta-line">Завантажую відгуки...</p>
            ) : teacherReviews.length === 0 ? (
              <p className="empty-state">
                Поки що немає відгуків по ваших завершених заняттях.
              </p>
            ) : (
              <div className="analytics-list">
                {teacherReviews.slice(0, 10).map((review) => (
                  <article
                    key={review.review_id}
                    className="analytics-item review-item"
                  >
                    <p>
                      <strong>
                        {"⭐".repeat(review.rating)} ({review.rating}/5)
                      </strong>{" "}
                      · {review.discipline_name}
                    </p>
                    <p className="meta-line">Студент: {review.student_name}</p>
                    <p className="meta-line">
                      {review.comment || "Без текстового коментаря."}
                    </p>
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

                <label className="span-all-columns">
                  Опис заняття (необов'язково)
                  <textarea
                    name="description"
                    value={editingSlotForm.description}
                    onChange={handleEditSlotFormChange}
                    placeholder="Наприклад: теми заняття, домашнє завдання, посилання на матеріали"
                    rows={3}
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
                      Опис: {expandedTeacherSlot.description || "Не вказано"}
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

                <div className="inline-actions">
                  <button
                    type="button"
                    className="ghost"
                    onClick={() =>
                      void handleTeacherCompleteAllBookings(
                        expandedTeacherSlotId,
                      )
                    }
                    disabled={
                      teacherBookingActionKey ===
                      `${expandedTeacherSlotId}:all:complete`
                    }
                  >
                    {teacherBookingActionKey ===
                    `${expandedTeacherSlotId}:all:complete`
                      ? "Завершую..."
                      : "Завершити всі ACTIVE"}
                  </button>
                </div>

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
              <h2>Створити викладача</h2>
              <form
                className="profile-form"
                onSubmit={handleCreateTeacherAccount}
              >
                <label>
                  Username
                  <input
                    name="username"
                    value={teacherRegistrationForm.username}
                    onChange={handleTeacherRegistrationFieldChange}
                    placeholder="teacher_new"
                    autoComplete="off"
                  />
                </label>

                <label>
                  ПІБ
                  <input
                    name="fullName"
                    value={teacherRegistrationForm.fullName}
                    onChange={handleTeacherRegistrationFieldChange}
                    placeholder="Іван Іваненко"
                  />
                </label>

                <label>
                  Email
                  <input
                    name="email"
                    type="email"
                    value={teacherRegistrationForm.email}
                    onChange={handleTeacherRegistrationFieldChange}
                    onBlur={handleTeacherRegistrationEmailBlur}
                    placeholder="teacher@example.com"
                    autoComplete="off"
                  />
                </label>

                {teacherRegistrationEmailError ? (
                  <p className="field-error">{teacherRegistrationEmailError}</p>
                ) : null}

                <label>
                  Password
                  <input
                    name="password"
                    type="password"
                    value={teacherRegistrationForm.password}
                    onChange={handleTeacherRegistrationFieldChange}
                    placeholder="Не менше 6 символів"
                    autoComplete="new-password"
                  />
                </label>

                <label>
                  Підтвердіть Password
                  <input
                    name="confirmPassword"
                    type="password"
                    value={teacherRegistrationForm.confirmPassword}
                    onChange={handleTeacherRegistrationFieldChange}
                    placeholder="Повторіть пароль"
                    autoComplete="new-password"
                  />
                </label>

                <label>
                  Місто
                  <select
                    name="cityId"
                    value={teacherRegistrationForm.cityId}
                    onChange={handleTeacherRegistrationFieldChange}
                    disabled={cities.length === 0}
                  >
                    <option value="">Оберіть місто</option>
                    {cities.map((city) => (
                      <option key={city.id} value={city.id}>
                        {city.name}
                      </option>
                    ))}
                  </select>
                </label>

                <p className="hint-text">
                  Під капотом форма створює профіль викладача, а потім одразу
                  створює акаунт доступу і прив'язує його до нового профілю.
                </p>

                {cities.length === 0 ? (
                  <p className="empty-state">
                    Для створення викладача потрібен довідник міст.
                  </p>
                ) : null}

                <button
                  type="submit"
                  disabled={
                    isTeacherRegistrationSubmitting || cities.length === 0
                  }
                >
                  {isTeacherRegistrationSubmitting ? "Створюю..." : "Створити"}
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
              <p className="meta-line">Сторінка {teacherAnalyticsPage}</p>
              {teacherAnalyticsRows.length === 0 && !isAdminAnalyticsLoading ? (
                <p className="empty-state">
                  Немає даних за поточними фільтрами.
                </p>
              ) : (
                <div className="analytics-list">
                  {teacherAnalyticsRows.map((row) => (
                    <article key={row.teacher_id} className="analytics-item">
                      <p>
                        <strong>{row.teacher_name}</strong> · {row.city_name}
                      </p>
                      <p className="meta-line">
                        ⭐{" "}
                        {row.average_rating != null
                          ? Number(row.average_rating).toFixed(1)
                          : "-"}
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

              <div className="inline-actions analytics-pagination">
                <button
                  type="button"
                  className="ghost"
                  onClick={handlePreviousTeacherAnalyticsPage}
                  disabled={
                    isAdminAnalyticsLoading || teacherAnalyticsPage === 1
                  }
                >
                  Назад
                </button>
                <button
                  type="button"
                  className="ghost"
                  onClick={handleNextTeacherAnalyticsPage}
                  disabled={isAdminAnalyticsLoading || !hasMoreTeacherAnalytics}
                >
                  Далі
                </button>
              </div>
            </article>

            <article
              className="panel reveal"
              style={{ animationDelay: "400ms" }}
            >
              <h2>Попит за дисциплінами</h2>
              <p className="meta-line">Сторінка {disciplineAnalyticsPage}</p>
              {disciplineAnalyticsRows.length === 0 &&
              !isAdminAnalyticsLoading ? (
                <p className="empty-state">
                  Немає даних за поточними фільтрами.
                </p>
              ) : (
                <div className="analytics-list">
                  {disciplineAnalyticsRows.map((row) => (
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

              <div className="inline-actions analytics-pagination">
                <button
                  type="button"
                  className="ghost"
                  onClick={handlePreviousDisciplineAnalyticsPage}
                  disabled={
                    isAdminAnalyticsLoading || disciplineAnalyticsPage === 1
                  }
                >
                  Назад
                </button>
                <button
                  type="button"
                  className="ghost"
                  onClick={handleNextDisciplineAnalyticsPage}
                  disabled={
                    isAdminAnalyticsLoading || !hasMoreDisciplineAnalytics
                  }
                >
                  Далі
                </button>
              </div>
            </article>
          </section>
        </>
      ) : null}
    </div>
  );
}

export default App;
