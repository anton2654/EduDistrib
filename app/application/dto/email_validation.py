from __future__ import annotations

from pydantic import EmailStr

# Common typo domains that frequently appear instead of valid providers.
COMMON_EMAIL_DOMAIN_TYPOS: dict[str, str] = {
    "gmail.co": "gmail.com",
    "gmail.con": "gmail.com",
    "gmai.com": "gmail.com",
    "gmial.com": "gmail.com",
    "gmal.com": "gmail.com",
    "outlok.com": "outlook.com",
    "outllok.com": "outlook.com",
}

# Known providers that only use one canonical domain.
CANONICAL_EMAIL_PROVIDER_DOMAINS: dict[str, str] = {
    "gmail": "gmail.com",
    "outlook": "outlook.com",
    "hotmail": "hotmail.com",
    "icloud": "icloud.com",
    "yahoo": "yahoo.com",
}


def normalize_email_input(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip().lower()
    if not normalized:
        raise ValueError("email cannot be blank")

    return normalized


def ensure_not_common_email_typo(value: EmailStr | None) -> EmailStr | None:
    if value is None:
        return None

    _, _, domain = str(value).partition("@")
    if domain in COMMON_EMAIL_DOMAIN_TYPOS:
        raise ValueError("Email domain looks incorrect.")

    provider_label = domain.split(".", 1)[0]
    canonical_domain = CANONICAL_EMAIL_PROVIDER_DOMAINS.get(provider_label)
    if canonical_domain is not None and domain != canonical_domain:
        raise ValueError("Email domain looks incorrect.")

    return value
