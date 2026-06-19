# Vue.js Localization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add English and Ukrainian localization to Vue.js pages with auto-detection from browser language, manual toggle override, and language persistence.

**Architecture:** Install vue-i18n and configure it with English and Ukrainian translation files. Create a composable for language detection/switching that reads `navigator.language`, checks localStorage, and falls back to English. Add a language toggle button to the App component. Replace all hardcoded strings in components with `$t()` calls and use `$d()` for date formatting with locale-aware formatting.

**Tech Stack:** Vue 3, Vite, vue-i18n 10.x, JSON translation files, localStorage for persistence

---

## File Structure

```
frontend/
├── src/
│   ├── locales/
│   │   ├── en.json              (English translations)
│   │   └── uk.json              (Ukrainian translations)
│   ├── i18n.js                  (i18n configuration & setup)
│   ├── components/
│   │   ├── LanguageToggle.vue    (Language switcher button)
│   │   ├── ShortenForm.vue       (Updated with $t() calls)
│   │   └── UrlList.vue           (Updated with $t() and $d() calls)
│   ├── App.vue                  (Updated: add LanguageToggle)
│   └── main.js                  (Updated: install i18n plugin)
└── package.json                 (Updated: add vue-i18n dependency)
```

---

## Tasks

### Task 1: Install vue-i18n

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Add vue-i18n dependency**

```bash
cd /Users/heknt/proj/url-shortener/frontend
npm install vue-i18n@11.4.6
```

Expected: npm installs successfully, `node_modules/vue-i18n` exists

- [ ] **Step 2: Verify installation**

```bash
npm list vue-i18n
```

Expected: Output shows `vue-i18n@11.4.6`

- [ ] **Step 3: Commit**

```bash
git add package.json package-lock.json
git commit -m "deps: add vue-i18n for localization support"
```

---

### Task 2: Create English translation file

**Files:**
- Create: `frontend/src/locales/en.json`

- [ ] **Step 1: Create locales directory**

```bash
mkdir -p /Users/heknt/proj/url-shortener/frontend/src/locales
```

- [ ] **Step 2: Write English translations**

Create `/Users/heknt/proj/url-shortener/frontend/src/locales/en.json`:

```json
{
  "common": {
    "language": "English"
  },
  "shortenForm": {
    "signInHint": "Sign in to access your private URLs and delete any links you no longer need.",
    "label": "paste a link, get something shorter",
    "urlPlaceholder": "https://example.com",
    "customCodePlaceholder": "custom code (optional)",
    "makePublic": "Make public (listed on Public urls)",
    "shortenButton": "Shorten",
    "resultPlaceholder": "your short link will appear here",
    "copyButton": "Copy",
    "errorPrefix": ""
  },
  "urlList": {
    "loading": "Loading…",
    "error": "Error loading URLs",
    "table": {
      "number": "#",
      "shortLink": "Short link",
      "originalLink": "Original link",
      "created": "Created",
      "visitCounter": "Visit counter",
      "status": "Status",
      "actions": "Actions",
      "public": "Public",
      "private": "Private"
    },
    "deleteButton": "Delete",
    "deleteConfirm": "Delete this link? It will no longer redirect.",
    "deleteSuccess": "Link deleted successfully"
  }
}
```

- [ ] **Step 3: Verify file exists**

```bash
cat /Users/heknt/proj/url-shortener/frontend/src/locales/en.json
```

Expected: JSON file with all English translations displays

- [ ] **Step 4: Commit**

```bash
git add frontend/src/locales/en.json
git commit -m "i18n: add English translations"
```

---

### Task 3: Create Ukrainian translation file

**Files:**
- Create: `frontend/src/locales/uk.json`

- [ ] **Step 1: Write Ukrainian translations**

Create `/Users/heknt/proj/url-shortener/frontend/src/locales/uk.json`:

```json
{
  "common": {
    "language": "Українська"
  },
  "shortenForm": {
    "signInHint": "Увійдіть, щоб отримати доступ до ваших приватних посилань та видаляти посилання, які вам більше не потрібні.",
    "label": "вставте посилання, отримайте щось коротше",
    "urlPlaceholder": "https://приклад.com",
    "customCodePlaceholder": "користувацький код (необов'язково)",
    "makePublic": "Зробити публічним (з'явиться на Публічних посиланнях)",
    "shortenButton": "Скоротити",
    "resultPlaceholder": "ваше коротке посилання з'явиться тут",
    "copyButton": "Копіювати",
    "errorPrefix": ""
  },
  "urlList": {
    "loading": "Завантаження…",
    "error": "Помилка завантаження посилань",
    "table": {
      "number": "№",
      "shortLink": "Коротке посилання",
      "originalLink": "Оригінальне посилання",
      "created": "Створено",
      "visitCounter": "Кількість переходів",
      "status": "Статус",
      "actions": "Дії",
      "public": "Публічне",
      "private": "Приватне"
    },
    "deleteButton": "Видалити",
    "deleteConfirm": "Видалити це посилання? Воно більше не буде перенаправляти.",
    "deleteSuccess": "Посилання видалено успішно"
  }
}
```

- [ ] **Step 2: Verify file exists**

```bash
cat /Users/heknt/proj/url-shortener/frontend/src/locales/uk.json
```

Expected: JSON file with all Ukrainian translations displays

- [ ] **Step 3: Commit**

```bash
git add frontend/src/locales/uk.json
git commit -m "i18n: add Ukrainian translations"
```

---

### Task 4: Create i18n configuration file

**Files:**
- Create: `frontend/src/i18n.js`

- [ ] **Step 1: Write i18n configuration**

Create `/Users/heknt/proj/url-shortener/frontend/src/i18n.js`:

```javascript
import { createI18n } from "vue-i18n";
import en from "./locales/en.json";
import uk from "./locales/uk.json";

// Detect browser language
function detectLanguage() {
  // Check localStorage first
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
```

- [ ] **Step 2: Verify file exists and syntax is correct**

```bash
node -c /Users/heknt/proj/url-shortener/frontend/src/i18n.js
```

Expected: No syntax errors output

- [ ] **Step 3: Commit**

```bash
git add frontend/src/i18n.js
git commit -m "i18n: create i18n configuration with language detection"
```

---

### Task 5: Setup i18n in main.js

**Files:**
- Modify: `frontend/src/main.js`

- [ ] **Step 1: Update main.js to install i18n plugin**

Current content of `/Users/heknt/proj/url-shortener/frontend/src/main.js`:
```javascript
import { createApp } from "vue";
import App from "./App.vue";
import router from "./router.js";

createApp(App).use(router).mount("#app");
```

Replace with:
```javascript
import { createApp } from "vue";
import App from "./App.vue";
import router from "./router.js";
import i18n from "./i18n.js";

createApp(App).use(i18n).use(router).mount("#app");
```

- [ ] **Step 2: Verify the file was updated**

```bash
grep -A 5 "createApp(App)" /Users/heknt/proj/url-shortener/frontend/src/main.js
```

Expected: Output shows `.use(i18n).use(router)`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/main.js
git commit -m "i18n: register i18n plugin in main.js"
```

---

### Task 6: Create LanguageToggle component

**Files:**
- Create: `frontend/src/components/LanguageToggle.vue`

- [ ] **Step 1: Write LanguageToggle component**

Create `/Users/heknt/proj/url-shortener/frontend/src/components/LanguageToggle.vue`:

```vue
<template>
  <div class="language-toggle">
    <button
      v-for="lang in languages"
      :key="lang.code"
      :class="['lang-btn', { active: i18n.locale === lang.code }]"
      @click="setLanguage(lang.code)"
    >
      {{ lang.name }}
    </button>
  </div>
</template>

<script setup>
import { useI18n } from "vue-i18n";

const i18n = useI18n();

const languages = [
  { code: "en", name: "EN" },
  { code: "uk", name: "UA" },
];

function setLanguage(lang) {
  i18n.locale = lang;
  localStorage.setItem("lang", lang);
}
</script>

<style scoped>
.language-toggle {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.lang-btn {
  padding: 0.35rem 0.65rem;
  border: 1px solid var(--bs-border-color, #dee2e6);
  background: transparent;
  color: inherit;
  border-radius: 0.4rem;
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: 500;
  transition: background 0.15s, border-color 0.15s;
}

.lang-btn:hover {
  border-color: var(--bs-secondary-color, #6c757d);
  background: var(--bs-tertiary-bg, #f8f9fa);
}

.lang-btn.active {
  background: var(--bs-primary, #0d6efd);
  color: white;
  border-color: var(--bs-primary, #0d6efd);
}
</style>
```

- [ ] **Step 2: Verify file exists**

```bash
cat /Users/heknt/proj/url-shortener/frontend/src/components/LanguageToggle.vue | head -20
```

Expected: Vue component code displays

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/LanguageToggle.vue
git commit -m "feat: add language toggle component"
```

---

### Task 7: Update App.vue to include LanguageToggle

**Files:**
- Modify: `frontend/src/App.vue`

- [ ] **Step 1: Update App.vue**

Current content:
```vue
<template>
  <RouterView />
</template>

<script setup>
import { RouterView } from "vue-router";
</script>
```

Replace with:
```vue
<template>
  <div class="app-container">
    <header class="app-header">
      <LanguageToggle />
    </header>
    <RouterView />
  </div>
</template>

<script setup>
import { RouterView } from "vue-router";
import LanguageToggle from "./components/LanguageToggle.vue";
</script>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.app-header {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--bs-border-color, #dee2e6);
  background: var(--bs-body-bg, #ffffff);
}
</style>
```

- [ ] **Step 2: Verify the file was updated**

```bash
grep -A 3 "LanguageToggle" /Users/heknt/proj/url-shortener/frontend/src/App.vue
```

Expected: Import and component usage visible

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.vue
git commit -m "feat: add language toggle to app header"
```

---

### Task 8: Update ShortenForm.vue to use i18n

**Files:**
- Modify: `frontend/src/components/ShortenForm.vue`

- [ ] **Step 1: Replace template strings with $t() calls**

Update `/Users/heknt/proj/url-shortener/frontend/src/components/ShortenForm.vue` template section (lines 1-54) to:

```vue
<template>
  <div class="page-wrap">
    <div class="spacer-top">
      <div class="hint-bar" :class="{ 'hint-bar--gone': !showHint }">
        <span>{{ $t('shortenForm.signInHint') }}</span>
        <button class="hint-close" @click="showHint = false" aria-label="Dismiss">×</button>
      </div>
    </div>

    <form @submit.prevent="submit" class="shorten-card">
      <p class="card-label">{{ $t('shortenForm.label') }}</p>

      <input
        v-model="inputUrl"
        type="text"
        :placeholder="$t('shortenForm.urlPlaceholder')"
        class="url-input"
      />

      <div class="options-row">
        <div class="code-wrap">
          <span class="code-prefix">{{ host }}/</span>
          <input
            v-model="customCode"
            type="text"
            :placeholder="$t('shortenForm.customCodePlaceholder')"
            class="code-input"
            maxlength="20"
          />
        </div>
        <label class="public-toggle">
          <input type="checkbox" v-model="isPublic" />
          {{ $t('shortenForm.makePublic') }}
        </label>
      </div>

      <div class="btn-row">
        <button class="btn-shorten" type="submit">{{ $t('shortenForm.shortenButton') }}</button>
      </div>

      <div class="result-box" :class="{ 'result-box--filled': result }">
        <a
          v-if="result"
          :href="result"
          target="_blank"
          rel="noopener noreferrer"
          class="result-link"
        >{{ result }}</a>
        <span v-else class="result-placeholder">{{ $t('shortenForm.resultPlaceholder') }}</span>
        <button v-if="result" class="btn-copy" type="button" @click="copy">{{ $t('shortenForm.copyButton') }}</button>
      </div>

      <p v-if="error" class="error-msg">{{ error }}</p>
    </form>
    <div class="spacer-bottom"></div>
  </div>
</template>
```

- [ ] **Step 2: Add i18n import to script section**

Add to the script setup section (after imports):
```javascript
import { useI18n } from "vue-i18n";

const { t } = useI18n();
```

Full updated script section:
```javascript
<script setup>
import { ref, computed } from "vue";
import { useI18n } from "vue-i18n";
import { shortenUrl } from "../api.js";

const { t } = useI18n();

const inputUrl = ref("");
const customCode = ref("");
const isPublic = ref(false);
const result = ref("");
const error = ref("");
const showHint = ref(!window.__isAuthenticated);

const host = computed(() => window.location.host);

async function submit() {
  error.value = "";
  result.value = "";
  try {
    const data = await shortenUrl(inputUrl.value, {
      code: customCode.value,
      isPublic: isPublic.value,
    });
    result.value = data.url;
  } catch (err) {
    error.value = err.message;
  }
}

function copy() {
  navigator.clipboard.writeText(result.value).catch(() => {
    prompt("Copy to clipboard: Ctrl+C, Enter", result.value);
  });
}
</script>
```

- [ ] **Step 3: Verify the changes**

```bash
grep -A 5 "shortenForm.label" /Users/heknt/proj/url-shortener/frontend/src/components/ShortenForm.vue
```

Expected: `$t('shortenForm.label')` visible

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ShortenForm.vue
git commit -m "i18n: localize ShortenForm component strings"
```

---

### Task 9: Update UrlList.vue to use i18n with date localization

**Files:**
- Modify: `frontend/src/components/UrlList.vue`

- [ ] **Step 1: Replace template strings and update table**

Update `/Users/heknt/proj/url-shortener/frontend/src/components/UrlList.vue` template section (lines 1-37):

```vue
<template>
  <div class="container-fluid py-3">
    <p v-if="loading">{{ $t('urlList.loading') }}</p>
    <p v-else-if="errorMsg" class="text-danger">{{ $t('urlList.error') }}</p>
    <div v-else class="table-responsive">
      <table class="table table-bordered table-striped table-sm">
        <thead class="table-dark">
        <tr>
          <th>{{ $t('urlList.table.number') }}</th>
          <th>{{ $t('urlList.table.shortLink') }}</th>
          <th>{{ $t('urlList.table.originalLink') }}</th>
          <th>{{ $t('urlList.table.created') }}</th>
          <th>{{ $t('urlList.table.visitCounter') }}</th>
          <th v-if="props.mode === 'mine'">{{ $t('urlList.table.status') }}</th>
          <th v-if="props.mode === 'mine'">{{ $t('urlList.table.actions') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(url, index) in urls" :key="url.short_url">
          <td>{{ index + 1 }}</td>
          <td><a :href="url.short_url">{{ url.short_url }}</a></td>
          <td><a :href="url.given_url">{{ url.given_url }}</a></td>
          <td>{{ $d(new Date(url.created_date), 'short') }}</td>
          <td>{{ url.visit_count }}</td>
          <td v-if="props.mode === 'mine'">
            <span :class="url.is_public ? 'badge bg-success' : 'badge bg-secondary'">
              {{ url.is_public ? $t('urlList.table.public') : $t('urlList.table.private') }}
            </span>
          </td>
          <td v-if="props.mode === 'mine'">
            <button class="btn btn-danger btn-sm" @click="confirmDelete(url)">{{ $t('urlList.deleteButton') }}</button>
          </td>
        </tr>
      </tbody>
    </table>
    </div>
  </div>
</template>
```

- [ ] **Step 2: Update script section with i18n and confirm message**

Replace the entire script section with:

```javascript
<script setup>
import { ref, onMounted, watch } from "vue";
import { useI18n } from "vue-i18n";
import { fetchPublicUrls, fetchMyUrls, deleteUrl } from "../api.js";

const props = defineProps({
  mode: { type: String, required: true },
});

const { t } = useI18n();

const urls = ref([]);
const loading = ref(true);
const errorMsg = ref("");

async function load() {
  loading.value = true;
  errorMsg.value = "";
  try {
    urls.value = props.mode === "mine" ? await fetchMyUrls() : await fetchPublicUrls();
  } catch (err) {
    errorMsg.value = err.message;
  } finally {
    loading.value = false;
  }
}

async function confirmDelete(url) {
  if (!confirm(t('urlList.deleteConfirm'))) return;
  try {
    await deleteUrl(url.id);
    urls.value = urls.value.filter((u) => u.id !== url.id);
  } catch (err) {
    alert(err.message);
  }
}

onMounted(load);
watch(() => props.mode, load);
</script>
```

- [ ] **Step 3: Verify the changes**

```bash
grep "\$t('urlList" /Users/heknt/proj/url-shortener/frontend/src/components/UrlList.vue | head -5
```

Expected: Multiple `$t('urlList...` calls visible

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/UrlList.vue
git commit -m "i18n: localize UrlList component with date formatting"
```

---

### Task 10: Build and test the implementation

**Files:**
- No files created/modified, verification only

- [ ] **Step 1: Build the frontend**

```bash
cd /Users/heknt/proj/url-shortener/frontend
npm run build
```

Expected: Build succeeds with no errors, `dist/` directory updated

- [ ] **Step 2: Start dev server and test**

```bash
cd /Users/heknt/proj/url-shortener/frontend
npm run dev &
```

Expected: Dev server starts on http://localhost:5173

- [ ] **Step 3: Verify language toggle appears**

Open http://localhost:5173 in browser and check:
- Language toggle buttons (EN/UA) visible in top-right
- Both buttons functional

Expected: Buttons appear and can be clicked

- [ ] **Step 4: Test language switching**

- Click EN button, verify English text displays
- Click UA button, verify Ukrainian text displays
- Check console for no errors

Expected: Text changes, localStorage persists language choice

- [ ] **Step 5: Test auto-detection by checking localStorage**

In browser console:
```javascript
localStorage.clear();
location.reload();
```

Expected: Page reloads and detects browser language (English if browser is English)

- [ ] **Step 6: Test date formatting**

Navigate to "Public urls" or "My URLs" and verify dates display in locale format. For Ukrainian, dates should show Ukrainian month abbreviations.

Expected: Dates appear correctly formatted in current language

- [ ] **Step 7: Kill dev server**

```bash
pkill -f "npm run dev"
```

- [ ] **Step 8: Final commit**

```bash
git add -A
git commit -m "i18n: implement full localization with English and Ukrainian support"
```

---
