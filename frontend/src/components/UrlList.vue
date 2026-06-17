<template>
  <div class="container-fluid py-3">
    <p v-if="loading">Loading…</p>
    <p v-else-if="errorMsg" class="text-danger">{{ errorMsg }}</p>
    <div v-else class="table-responsive">
      <table class="table table-bordered table-striped table-sm">
        <thead class="table-dark">
        <tr>
          <th>#</th>
          <th>Short link</th>
          <th>Original link</th>
          <th>Created</th>
          <th>Visit counter</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(url, index) in urls" :key="url.short_url">
          <td>{{ index + 1 }}</td>
          <td><a :href="url.short_url">{{ url.short_url }}</a></td>
          <td><a :href="url.given_url">{{ url.given_url }}</a></td>
          <td>{{ formatDate(url.created_date) }}</td>
          <td>{{ url.visit_count }}</td>
        </tr>
      </tbody>
    </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from "vue";
import { fetchPublicUrls, fetchMyUrls } from "../api.js";

const props = defineProps({
  mode: { type: String, required: true },
});

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

function formatDate(isoString) {
  return new Date(isoString).toLocaleString(undefined, {
    year: "numeric", month: "short", day: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

onMounted(load);
watch(() => props.mode, load);
</script>
