<template>
  <v-dialog v-model="dialog" width="600px">
    <v-card>
      <v-toolbar color="primary">
        <v-toolbar-title class="text-h6">
          {{ $t("modal.admin.update_account.title") }}
        </v-toolbar-title>

        <template #append>
          <v-btn icon="mdi-close" @click="dialog = false" variant="plain" color="grey" />
        </template>
      </v-toolbar>

      <v-card-text class="scrollable-content">
        <v-row>
          <v-col cols="12" md="12">
            <div class="text-subtitle-1 text-medium-emphasis">
              {{ $t("modal.admin.update_account.email") }}
            </div>
            <v-text-field
              v-model="emailLocal"
              :rules="[checkLength]"
              density="compact"
              variant="outlined"
            />
          </v-col>

          <v-col cols="12" md="12" class="mt-n8">
            <div class="text-subtitle-1 text-medium-emphasis">
              {{ $t("modal.admin.update_account.role") }}
            </div>
            <v-select
              v-model="roleLocal"
              :items="roleOptions"
              item-title="label"
              item-value="value"
              density="compact"
              variant="outlined"
            />
          </v-col>

          <v-col cols="12" md="12" class="mt-n8">
            <div class="text-subtitle-1 text-medium-emphasis">
              {{ $t("modal.admin.update_account.max_storage_size") }}
            </div>
            <v-text-field v-model="maxStorageSizeLocal" density="compact" variant="outlined" />
          </v-col>

          <v-col cols="12" md="12" class="mt-n8">
            <div class="text-subtitle-1 text-medium-emphasis">
              {{ $t("modal.admin.update_account.max_video_size") }}
            </div>
            <v-text-field v-model="maxVideoSizeLocal" density="compact" variant="outlined" />
          </v-col>

          <v-col cols="12" md="12" class="mt-n8">
            <div class="text-subtitle-1 text-medium-emphasis">
              {{ $t("modal.admin.update_account.max_file_size") }}
            </div>
            <v-text-field v-model="maxFileSizeLocal" density="compact" variant="outlined" />
          </v-col>
        </v-row>
      </v-card-text>

      <v-card-actions class="mb-2">
        <v-btn
          color="primary"
          variant="tonal"
          class="mr-8"
          :disabled="!canSave"
          @click="saveSettings"
          >{{ $t("button.save") }}</v-btn
        >
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useAdminStore } from "@/stores/admin";

const adminStore = useAdminStore();

const { t } = useI18n();

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  user: {
    type: Object,
    required: true,
  },
});
const emit = defineEmits();

const dialog = ref(props.modelValue);
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
    }
  }
);

const emailLocal = ref("");
const roleLocal = ref("");
const maxStorageSizeLocal = ref(0);
const maxVideoSizeLocal = ref(0);
const maxFileSizeLocal = ref(0);
watch(
  () => props.user,
  (newUser) => {
    if (newUser) {
      emailLocal.value = newUser.email || "";
      roleLocal.value = newUser.role || "user";
      maxStorageSizeLocal.value = newUser.max_storage_size || 0;
      maxVideoSizeLocal.value = newUser.max_video_size || 0;
      maxFileSizeLocal.value = newUser.max_file_size || 0;
    }
  },
  { immediate: true }
);

const checkLength = (value) => {
  if (!value) {
    return t("field.required");
  }
  if (value.length < 5) {
    return t("user.register.rules.min");
  }
  if (value.length > 50) {
    return t("user.register.rules.max");
  }
  return true;
};

const roleOptions = [
  { label: t("modal.admin.update_account.roles.admin"), value: "admin" },
  { label: t("modal.admin.update_account.roles.user"), value: "user" },
];

const canSave = computed(() => {
  return (
    emailLocal.value !== props.user.email ||
    roleLocal.value !== props.user.role ||
    maxStorageSizeLocal.value !== props.user.max_storage_size ||
    maxVideoSizeLocal.value !== props.user.max_video_size ||
    maxFileSizeLocal.value !== props.user.max_file_size
  );
});

const saveSettings = async () => {
  if (!canSave.value) return;

  const params = {
    id: props.user.id,
    email: emailLocal.value,
    role: roleLocal.value,
    max_storage_size: maxStorageSizeLocal.value,
    max_video_size: maxVideoSizeLocal.value,
    max_file_size: maxFileSizeLocal.value,
    update_type: "admin",
  };

  try {
    const res = await adminStore.updateUser(params);
    if (res.status === "ok") {
      emit("updated", res.data);
      dialog.value = false;
    }
  } catch (err) {
    console.error(err);
  }
};
</script>

<style scoped>
.scrollable-content {
  max-height: 500px;
  overflow-y: auto;
}
</style>
