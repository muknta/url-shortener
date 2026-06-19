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
