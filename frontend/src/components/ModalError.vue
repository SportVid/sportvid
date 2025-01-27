<template>
  <v-dialog v-model="dialog" max-width="90%">
    <v-card>
      <v-card-title class="mb-2">
        {{ $t("modal.error.title") }}

        <v-btn icon @click="clearError" absolute right>
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>
      <v-card-text>
        {{ errorMessage }}
      </v-card-text>
      <v-card-actions class="pt-0">
        <v-btn @click="clearError">{{ $t("modal.error.close") }}</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import { ref, computed, watch } from "vue";
import { useErrorStore } from "@/stores/error";

export default {
  setup() {
    const dialog = ref(false);

    const errorStore = useErrorStore();

    const errorDate = computed(() => errorStore.error_date);
    const errorComponent = computed(() => errorStore.error_component);
    const errorMessage = computed(() => errorStore.errorMessage);
    const error = computed(() => errorStore.error);

    const clearError = () => {
      dialog.value = false;
      errorStore.clearError(); 
    };

    watch(error, (value) => {
      if (value) {
        dialog.value = true;
      }
    });

    return {
      dialog,
      errorDate,
      errorComponent,
      errorMessage,
      error,
      clearError,
    };
  },
};
</script>
