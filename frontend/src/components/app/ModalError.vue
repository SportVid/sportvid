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
import { useErrorStore } from "@/stores/error";

const dialog = ref(false);

const errorStore = useErrorStore();

const errorMessage = computed(() => errorStore.errorMessage);

const error = computed(() => errorStore.error);

watch(error, (value) => {
  if (value) {
    dialog.value = true;
  }
});
</script>
