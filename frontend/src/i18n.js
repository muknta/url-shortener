import { createI18n } from "vue-i18n";
import en from "./locales/en.json";
import uk from "./locales/uk.json";

// Get cookie by name
function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(";").shift();
  return null;
}

// Detect browser language
function detectLanguage() {
  // Check Django language cookie first (highest priority)
  const djangoCookie = getCookie("django_language");
  if (djangoCookie && ["en", "uk"].includes(djangoCookie)) {
    localStorage.setItem("lang", djangoCookie);
    return djangoCookie;
  }

  // Check localStorage
  const saved = localStorage.getItem("lang");
  if (saved && ["en", "uk"].includes(saved)) {
    return saved;
  }

  // Auto-detect from browser
  const browserLang = navigator.language.split("-")[0];
  if (["en", "uk"].includes(browserLang)) {
    return browserLang;
  }

  // Default to English
  return "en";
}

// Date formatter
const dateTimeFormats = {
  en: {
    short: {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    },
  },
  uk: {
    short: {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    },
  },
};

const i18n = createI18n({
  legacy: false,
  locale: detectLanguage(),
  fallbackLocale: "en",
  messages: {
    en,
    uk,
  },
  datetimeFormats: dateTimeFormats,
});

export default i18n;
