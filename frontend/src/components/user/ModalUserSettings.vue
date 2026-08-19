<template>
  <v-dialog v-model="dialog" width="800px">
    <v-card class="login">
      <v-toolbar color="primary">
        <v-toolbar-title class="text-h6">
          {{ $t("modal.settings.title") }}
        </v-toolbar-title>

        <template #append>
          <v-btn icon="mdi-close" @click="dialog = false" variant="plain" color="grey" />
        </template>
      </v-toolbar>

      <v-card-text class="scrollable-content">
        <v-row>
          <v-col cols="12">
            <div class="text-h6">{{ $t("modal.settings.information") }}</div>
          </v-col>

          <v-col cols="12" md="12" class="mt-n4">
            <div class="text-subtitle-1 text-medium-emphasis">
              {{ $t("modal.settings.username") }}
            </div>
            <v-text-field
              v-model="usernameLocal"
              disabled
              density="compact"
              variant="outlined"
              class="readonly-field"
            />
          </v-col>

          <v-col cols="12" md="12" class="mt-n8">
            <div class="text-subtitle-1 text-medium-emphasis">
              {{ $t("modal.settings.joined") }}
            </div>
            <v-text-field
              v-model="joinedLocal"
              disabled
              density="compact"
              variant="outlined"
              class="readonly-field"
            />
          </v-col>

          <v-col cols="12" md="12" class="mt-n8">
            <div class="text-subtitle-1 text-medium-emphasis">
              {{ $t("modal.settings.email") }}
            </div>
            <v-text-field
              v-model="emailLocal"
              :rules="[checkLength]"
              density="compact"
              variant="outlined"
            />
          </v-col>
        </v-row>

        <v-divider class="my-2" />

        <v-row class="mt-2">
          <v-col cols="12">
            <div class="text-h6">{{ $t("modal.settings.experience_mode.title") }}</div>
          </v-col>
          <!-- Same grouped toggle+sentence pattern as ModalUserRegister.vue (compact toggle,
               a single docked sentence below that always reflects the current selection, no
               hover) -- but capped to a comfortable max-width and centered rather than
               stretched to this dialog's full (much wider) 750px content width, so the
               buttons don't end up looking oversized and the sentence still gets enough room
               to only wrap onto ~2 lines. -->
          <v-col cols="12" class="mt-n4 mb-4">
            <div>
              <v-sheet border rounded class="experience-mode-group">
                <v-btn-toggle
                  v-model="experienceModeLocal"
                  mandatory
                  divided
                  rounded="0"
                  density="comfortable"
                  class="d-flex"
                >
                  <v-btn
                    v-for="mode in ['simple', 'complex']"
                    :key="mode"
                    :value="mode"
                    class="flex-grow-1"
                  >
                    {{ $t(`user.experience_mode.${mode}_label`) }}
                  </v-btn>
                </v-btn-toggle>
                <v-divider />
                <div
                  class="pa-2 text-caption text-medium-emphasis"
                  :class="experienceModeLocal === 'complex' ? 'text-right' : 'text-left'"
                >
                  {{ $t(`user.experience_mode.${experienceModeLocal}_sentence`) }}
                </div>
              </v-sheet>
            </div>
          </v-col>
        </v-row>

        <v-divider class="my-2" />

        <v-row class="mt-2">
          <v-col cols="12">
            <div class="text-h6">{{ $t("modal.settings.security") }}</div>
          </v-col>
          <v-col cols="12" md="12" class="mt-n4">
            <div class="text-subtitle-1 text-medium-emphasis mb-2">
              {{ $t("modal.settings.password") }}
            </div>
            <v-row>
              <v-col cols="12" md="6">
                <v-text-field
                  v-model="currentPassword"
                  :label="$t('modal.settings.password_current')"
                  density="compact"
                  variant="outlined"
                  :rules="[checkPwdLength]"
                />
              </v-col>
              <v-col cols="12" md="6">
                <v-text-field
                  v-model="newPassword"
                  :label="$t('modal.settings.password_new')"
                  density="compact"
                  variant="outlined"
                  :rules="[checkPwdLength]"
                />
              </v-col>
            </v-row>

            <div v-if="passwordError" class="text-error text-center mt-2">{{ passwordError }}</div>
            <div v-if="generalServerError" class="text-error text-center mt-1">
              {{ generalServerError }}
            </div>
          </v-col>

          <v-col cols="12" md="12" class="mt-n8">
            <div class="text-subtitle-1 text-medium-emphasis mb-2">
              {{ $t("modal.settings.delete_account") }}
            </div>
            <v-btn color="error" variant="tonal" block @click="showModalDelete = true">
              {{ $t("button.delete") }}
            </v-btn>
            <ModalUserDelete v-model="showModalDelete" @deleted="handleDeleted" />
          </v-col>
        </v-row>
      </v-card-text>

      <v-card-actions class="mb-2">
        <v-btn :disabled="!canSave" @click="saveSettings" variant="tonal" class="mr-8">
          {{ $t("button.save") }}
        </v-btn>
      </v-card-actions>

      <v-snackbar v-model="showSettingsSnackbar">
        <div class="d-flex justify-center">
          <snackbar-icon-success />
          <span class="text-h6">{{ $t("modal.settings.settings_success") }}</span>
        </div>
      </v-snackbar>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, watch, computed } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { useUserStore } from "@/stores/user";
import ModalUserDelete from "@/components/user/ModalUserDelete.vue";

const userStore = useUserStore();
const router = useRouter();
const { t } = useI18n();

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
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

const usernameLocal = ref(userStore.username);
watch(
  () => userStore.username,
  (val) => {
    if (dialog.value) usernameLocal.value = val;
  }
);

const emailLocal = ref(userStore.email);
const hasEmailChanged = () => emailLocal.value !== userStore.email;

// Unlike dashboardLayout/videoViewMode (saved immediately on change elsewhere), this needs to
// go through the same explicit "Save" button as email/password below -- so the toggle only
// edits this local copy; saveSettings() below is what actually persists it.
const experienceModeLocal = ref(userStore.experienceMode);
const hasExperienceModeChanged = () => experienceModeLocal.value !== userStore.experienceMode;
watch(
  () => userStore.email,
  (val) => {
    if (dialog.value) {
      emailLocal.value = val;
    }
  }
);

const formatDate = (s) => {
  if (!s) return "";
  try {
    return s.split("T")[0];
  } catch (e) {
    return s;
  }
};
const joinedLocal = ref(formatDate(userStore.dateJoined));
watch(
  () => userStore.dateJoined,
  (val) => {
    if (dialog.value) joinedLocal.value = formatDate(val);
  }
);

const currentPassword = ref(null);
const newPassword = ref(null);
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
const checkPwdLength = (value) => {
  if (!value) return true;
  return checkLength(value);
};

watch(
  () => props.modelValue,
  (value) => {
    if (value) {
      dialog.value = true;
      emailLocal.value = userStore.email;
      usernameLocal.value = userStore.username;
      joinedLocal.value = formatDate(userStore.dateJoined);
      experienceModeLocal.value = userStore.experienceMode;
    }
  }
);

const passwordError = ref(null);
const generalServerError = ref(null);

const canSave = computed(() => {
  const emailChanged = hasEmailChanged();
  const experienceModeChanged = hasExperienceModeChanged();
  const pwdCurrentVal = currentPassword.value;
  const pwdNewVal = newPassword.value;
  const pwdAny = !!pwdCurrentVal || !!pwdNewVal;

  if (!emailChanged && !experienceModeChanged && !pwdAny) return false;

  if (emailChanged) {
    if (checkLength(emailLocal.value) !== true) return false;
  }

  if ((pwdCurrentVal && !pwdNewVal) || (!pwdCurrentVal && pwdNewVal)) return false;
  if (pwdCurrentVal && pwdNewVal) {
    if (checkLength(pwdNewVal) !== true) return false;
    if (!pwdCurrentVal) return false;
  }

  return true;
});
const saveSettings = async () => {
  showSettingsSnackbar.value = false;
  passwordError.value = null;
  generalServerError.value = null;

  const params = {};
  if (hasEmailChanged()) {
    params.email = emailLocal.value;
  }

  const pwdCurrentVal = currentPassword.value;
  const pwdNewVal = newPassword.value;

  if ((pwdCurrentVal && !pwdNewVal) || (!pwdCurrentVal && pwdNewVal)) {
    passwordError.value = t("modal.settings.password_both_required");
    return;
  }

  if (pwdCurrentVal && pwdNewVal) {
    if (checkLength(pwdNewVal) !== true) {
      passwordError.value = t("modal.settings.password_min", { min: 5 });
      return;
    }
    params.password_current = pwdCurrentVal;
    params.password_new = pwdNewVal;
  }

  const experienceModeChanged = hasExperienceModeChanged();

  if (Object.keys(params).length === 0 && !experienceModeChanged) {
    generalServerError.value = t("modal.settings.no_changes");
    return;
  }

  try {
    let ok = true;

    if (Object.keys(params).length > 0) {
      params.update_type = "user";
      const res = await userStore.updateUser(params);
      if (res && res.status === "ok") {
        currentPassword.value = null;
        newPassword.value = null;
      } else {
        ok = false;
        const msg = res && res.message ? res.message : null;

        if (msg) {
          if (msg === "Invalid current password") {
            passwordError.value = t("modal.settings.invalid_current_password");
          } else if (msg === "Both current and new passwords are required") {
            passwordError.value = t("modal.settings.password_both_required");
          } else {
            const lmsg = msg.toLowerCase();
            const numMatch = msg.match(/(\d+)/);
            if (lmsg.includes("short") || lmsg.includes("must contain") || numMatch) {
              const min = numMatch ? parseInt(numMatch[1], 10) : 5;
              passwordError.value = t("modal.settings.password_min", { min });
            } else if (
              lmsg.includes("too similar") ||
              lmsg.includes("too common") ||
              lmsg.includes("password")
            ) {
              passwordError.value = t("modal.settings.password_invalid");
            } else {
              generalServerError.value = t("modal.settings.update_failed");
            }
          }
        } else {
          generalServerError.value = t("modal.settings.update_failed");
        }
      }
    }

    if (ok && experienceModeChanged) {
      const res = await userStore.saveExperienceMode(experienceModeLocal.value);
      if (!(res && res.status === "ok")) {
        ok = false;
        generalServerError.value = t("modal.settings.update_failed");
      }
    }

    if (ok) {
      showSettingsSnackbar.value = true;
      passwordError.value = null;
      generalServerError.value = null;
    }
  } catch (err) {
    console.error(err);
    generalServerError.value = t("modal.settings.update_failed");
  }
};

const showModalDelete = ref(false);
const handleDeleted = () => {
  dialog.value = false;
  router.push({ name: "VideoView" });
};

const showSettingsSnackbar = ref(false);
</script>

<style scoped>
.readonly-field ::v-deep(.v-field) {
  opacity: 1 !important;
}

.scrollable-content {
  max-height: 500px;
  overflow-y: auto;
}

.experience-mode-group {
  overflow: hidden;
}
</style>
