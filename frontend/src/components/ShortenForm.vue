<template>
  <div id="url-content">
    <form @submit.prevent="submit">
      <input v-model="inputUrl" type="text" placeholder="http://example.com" class="form-control" />
      <div class="buttons">
        <button class="btn btn-outline-secondary" type="submit">Shorten</button>
        <button
          v-if="result"
          class="btn btn-outline-primary"
          type="button"
          @click="copy"
        >
          Copy
        </button>
      </div>
      <span id="result">{{ result || "** dream link **" }}</span>
      <span v-if="error" class="text-danger">{{ error }}</span>
    </form>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { shortenUrl } from "../api.js";

const inputUrl = ref("");
const result = ref("");
const error = ref("");

async function submit() {
  error.value = "";
  result.value = "";
  try {
    const data = await shortenUrl(inputUrl.value);
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
