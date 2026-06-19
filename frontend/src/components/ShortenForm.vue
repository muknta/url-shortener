<template>
  <div class="page-wrap">
    <div class="hint-bar">
      <span>Sign in to access your private URLs and delete any links you no longer need.</span>
      <button class="hint-close" @click="showHint = false" aria-label="Dismiss">×</button>
    </div>
    <div class="spacer-top"></div>

    <form @submit.prevent="submit" class="shorten-card">
      <p class="card-label">paste a link, get something shorter</p>

      <input
        v-model="inputUrl"
        type="text"
        placeholder="https://example.com"
        class="url-input"
      />

      <div class="options-row">
        <div class="code-wrap">
          <span class="code-prefix">{{ host }}/</span>
          <input
            v-model="customCode"
            type="text"
            placeholder="custom code (optional)"
            class="code-input"
            maxlength="20"
          />
        </div>
        <label class="public-toggle">
          <input type="checkbox" v-model="isPublic" />
          Make public (listed on Public urls)
        </label>
      </div>

      <div class="btn-row">
        <button class="btn-shorten" type="submit">Shorten</button>
      </div>

      <div class="result-box" :class="{ 'result-box--filled': result }">
        <a
          v-if="result"
          :href="result"
          target="_blank"
          rel="noopener noreferrer"
          class="result-link"
        >{{ result }}</a>
        <span v-else class="result-placeholder">your short link will appear here</span>
        <button v-if="result" class="btn-copy" type="button" @click="copy">Copy</button>
      </div>

      <p v-if="error" class="error-msg">{{ error }}</p>
    </form>
    <div class="spacer-bottom"></div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { shortenUrl } from "../api.js";

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

<style scoped>
.page-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-height: calc(100dvh - 56px - 3.5rem);
  padding: 0.5rem 1rem;
}

.spacer-top {
  flex: 3;
}

.spacer-bottom {
  flex: 4;
}

.hint-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  width: 100%;
  max-width: 560px;
  padding: 0.45rem 0.9rem;
  margin-bottom: 2.75rem;
  font-size: 0.8rem;
  color: var(--bs-secondary-color, #6c757d);
  border: 1px solid color-mix(in srgb, currentColor 20%, transparent);
  border-radius: 0.5rem;
  opacity: 0.7;
  transition: opacity 0.15s;
}

.hint-bar:hover {
  opacity: 1;
}

.hint-close {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.05rem;
  line-height: 1;
  color: inherit;
  padding: 0 0.1rem;
  opacity: 0.45;
  transition: opacity 0.15s;
}

.hint-close:hover {
  opacity: 1;
}

.shorten-card {
  width: 100%;
  max-width: 560px;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.card-label {
  margin: 0 0 0.25rem;
  font-size: 0.78rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--bs-secondary-color, #6c757d);
  opacity: 0.65;
}

.url-input {
  border: 1px solid var(--bs-border-color, #dee2e6);
  border-radius: 0.75rem;
  padding: 0.7rem 1rem;
  font-size: 1rem;
  background: transparent;
  color: inherit;
  outline: none;
  transition: border-color 0.18s, box-shadow 0.18s;
}

.url-input:focus {
  border-color: var(--bs-primary, #0d6efd);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--bs-primary, #0d6efd) 15%, transparent);
}

.btn-shorten {
  width: 100%;
  padding: 0.75rem 1.4rem;
  border-radius: 0.75rem;
  border: 1px solid var(--bs-border-color, #dee2e6);
  background: var(--bs-tertiary-bg, #f8f9fa);
  color: var(--bs-body-color, #212529);
  cursor: pointer;
  font-size: 0.95rem;
  font-weight: 500;
  white-space: nowrap;
  transition: background 0.15s, border-color 0.15s, box-shadow 0.15s;
}

.btn-shorten:hover {
  border-color: var(--bs-secondary-color, #6c757d);
  box-shadow: 0 1px 6px color-mix(in srgb, var(--bs-body-color, #000) 10%, transparent);
}

.btn-shorten:active {
  transform: translateY(1px);
}

.options-row {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.btn-row {
  display: flex;
  justify-content: center;
  padding-top: 10px;
}

.code-wrap {
  display: flex;
  align-items: center;
  border: 1px solid var(--bs-border-color, #dee2e6);
  border-radius: 0.75rem;
  overflow: hidden;
  background: transparent;
}

.code-prefix {
  padding: 0.55rem 0.75rem 0.55rem 1rem;
  font-size: 0.9rem;
  color: var(--bs-secondary-color, #6c757d);
  white-space: nowrap;
  border-right: 1px solid var(--bs-border-color, #dee2e6);
  user-select: none;
}

.code-input {
  flex: 1;
  border: none;
  outline: none;
  padding: 0.55rem 1rem;
  font-size: 0.9rem;
  background: transparent;
  color: inherit;
}

.public-toggle {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  font-size: 0.85rem;
  color: var(--bs-secondary-color, #6c757d);
  cursor: pointer;
  user-select: none;
}

.result-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 1.05rem 1.25rem;
  border-radius: 0.875rem;
  border: 1.5px dashed color-mix(in srgb, var(--bs-border-color, #dee2e6) 80%, transparent);
  background: transparent;
  min-height: 3.6rem;
  transition: border-color 0.25s, border-style 0.25s, box-shadow 0.3s, background 0.3s;
}

.result-box--filled {
  border-style: solid;
  border-color: var(--bs-primary, #0d6efd);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--bs-primary, #0d6efd) 12%, transparent);
  background: color-mix(in srgb, var(--bs-primary, #0d6efd) 4%, transparent);
}

.result-link {
  font-size: 1rem;
  word-break: break-all;
  color: var(--bs-primary, #0d6efd);
  text-decoration: none;
  font-weight: 500;
}

.result-link:hover {
  text-decoration: underline;
}

.result-placeholder {
  font-size: 0.85rem;
  font-style: italic;
  opacity: 0.3;
}

.btn-copy {
  flex-shrink: 0;
  padding: 0.35rem 0.95rem;
  border-radius: 0.55rem;
  border: 1px solid var(--bs-primary, #0d6efd);
  background: transparent;
  color: var(--bs-primary, #0d6efd);
  cursor: pointer;
  font-size: 0.8rem;
  white-space: nowrap;
  transition: background 0.15s, color 0.15s;
}

.btn-copy:hover {
  background: var(--bs-primary, #0d6efd);
  color: white;
}

.error-msg {
  margin: 0;
  font-size: 0.85rem;
  color: var(--bs-danger, #dc3545);
}
</style>
