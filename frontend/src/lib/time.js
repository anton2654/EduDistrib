const DATE_TIME_FORMATTER = new Intl.DateTimeFormat("uk-UA", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

export function formatDateTime(value) {
  const parsed = new Date(value);
  return DATE_TIME_FORMATTER.format(parsed);
}

export function formatDateTimeRange(start, end) {
  return `${formatDateTime(start)} - ${formatDateTime(end)}`;
}

function pad(value) {
  return String(value).padStart(2, "0");
}

export function toDateTimeLocalInputValue(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }

  const year = date.getFullYear();
  const month = pad(date.getMonth() + 1);
  const day = pad(date.getDate());
  const hours = pad(date.getHours());
  const minutes = pad(date.getMinutes());

  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

export function toIsoFromLocalInput(value) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    throw new Error("Некоректна дата або час.");
  }
  return parsed.toISOString();
}
