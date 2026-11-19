<template>
  <v-dialog v-model="dialog" width="900px">
    <v-card>
      <v-toolbar color="accent">
        <v-toolbar-title class="text-h6">
          {{ $t("modal.error.title") }}
        </v-toolbar-title>

        <template #append>
          <v-btn icon="mdi-close" @click="dialog = false" variant="plain" color="grey" />
        </template>
      </v-toolbar>

      <v-card-text>
        {{ errorMessage }}
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useErrorStore } from "@/stores/error";

const dialog = ref(false);

const errorStore = useErrorStore();
const { t, te } = useI18n();

// Known error codes (e.g. quota_exceeded from an upload) get a translated message;
// anything else is shown as the raw "component: code" line.
const errorMessage = computed(() => {
  const key = `modal.error.messages.${errorStore.error_code}`;
  return errorStore.error_code && te(key) ? t(key) : errorStore.errorMessage;
});

const error = computed(() => errorStore.error);

watch(error, (value) => {
  if (value) {
    dialog.value = true;
  }
});
</script>
