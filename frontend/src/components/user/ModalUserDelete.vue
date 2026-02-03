<template>
  <v-dialog v-model="dialog" width="800px">
    <v-card>
      <v-toolbar color="primary">
        <v-toolbar-title class="text-h6">
          {{ $t("modal.delete_account.title") }}
        </v-toolbar-title>

        <template #append>
          <v-btn icon="mdi-close" @click="dialog = false" variant="plain" color="grey" />
        </template>
      </v-toolbar>

      <v-card-text>
        <v-text-field
          v-model="password"
          :label="$t('user.password')"
          type="password"
          density="compact"
          variant="outlined"
          class="mt-2"
        />
        <div v-if="error" class="text-error mt-n4 mb-4">{{ error }}</div>

        <v-btn
          color="error"
          variant="tonal"
          block
          :disabled="!password || userStore.isLoading"
          @click="confirmDelete"
          >{{ $t("button.delete") }}
        </v-btn>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, watch } from "vue";
import { useUserStore } from "@/stores/user";
import { useI18n } from "vue-i18n";

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
});
const emit = defineEmits();
const userStore = useUserStore();

const dialog = ref(props.modelValue);
const password = ref(null);
const error = ref(null);

watch(
  () => dialog.value,
  (value) => {
    emit("update:modelValue", value);
  }
);

watch(
  () => props.modelValue,
  (value) => {
    if (value) {
      dialog.value = true;
      password.value = null;
      error.value = null;
    }
  }
);

const { t } = useI18n();

const confirmDelete = async () => {
  if (userStore.isLoading) return;
  try {
    const res = await userStore.deleteUser({ password: password.value });
    if (res && res.status === "ok") {
      dialog.value = false;
      emit("deleted");
    } else {
      const msg = res && res.message ? res.message : null;
      const allowed = ["Invalid password", "Password missing"];
      if (msg && allowed.includes(msg)) {
        error.value = msg;
      } else {
        error.value = t("modal.delete_account.error");
      }
    }
  } catch (err) {
    error.value = t("modal.delete_account.error");
  }
};

const cancel = () => {
  dialog.value = false;
};
</script>
