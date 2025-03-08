<template>
  <v-dialog v-model="dialog" max-width="90%">
    <v-card>
      <v-card-title class="mt-2 ml-2">
        <span class="text-accent">{{ $t("modal.error.title") }}</span>
      </v-card-title>
      <v-card-text>
        {{ errorMessage }}
      </v-card-text>
      <v-card-actions class="mb-2 mr-2">
        <v-btn @click="clearError" variant="elevated">{{ $t("modal.error.close") }}</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { useErrorStore } from "@/stores/error";

const dialog = ref(false);

const errorStore = useErrorStore();

const errorDate = computed(() => errorStore.error_date);
const errorComponent = computed(() => errorStore.error_component);
const errorMessage = computed(() => errorStore.errorMessage);
const error = computed(() => errorStore.error);

const clearError = () => {
  dialog.value = false;
};

watch(error, (value) => {
  if (value) {
    dialog.value = true;
  }
});
</script>
