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
