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
