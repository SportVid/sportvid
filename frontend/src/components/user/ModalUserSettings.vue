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
            <v-subheader class="text-h6">{{ $t("modal.settings.information") }}</v-subheader>
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
            <v-subheader class="text-h6">{{ $t("modal.settings.language") }}</v-subheader>
          </v-col>
          <v-col cols="12" md="6" class="mt-n4">
            <v-select
              v-model="selectedLanguage"
              :items="languageStore.languages"
              item-title="label"
              item-value="code"
              density="compact"
              variant="outlined"
            />
          </v-col>
        </v-row>

        <v-divider class="my-2" />

        <v-row class="mt-2">
          <v-col cols="12">
            <v-subheader class="text-h6">{{ $t("modal.settings.security") }}</v-subheader>
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
import { useLanguageStore } from "@/stores/languages";
import ModalUserDelete from "@/components/user/ModalUserDelete.vue";

const userStore = useUserStore();
const languageStore = useLanguageStore();
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
const joinedLocal = ref(formatDate(userStore.date));
watch(
  () => userStore.date,
  (val) => {
    if (dialog.value) joinedLocal.value = formatDate(val);
  }
);

const selectedLanguage = ref(languageStore.currentLanguage);
const hasLanguageChanged = () => selectedLanguage.value !== languageStore.currentLanguage;
watch(
  () => languageStore.currentLanguage,
  (val) => {
    if (dialog.value) {
      selectedLanguage.value = val;
    }
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
      selectedLanguage.value = languageStore.currentLanguage;
      emailLocal.value = userStore.email;
      usernameLocal.value = userStore.username;
      joinedLocal.value = formatDate(userStore.date);
    }
  }
);

const passwordError = ref(null);
const generalServerError = ref(null);

const canSave = computed(() => {
  const emailChanged = hasEmailChanged();
  const languageChanged = hasLanguageChanged();
  const pwdCurrentVal = currentPassword.value;
  const pwdNewVal = newPassword.value;
  const pwdAny = !!pwdCurrentVal || !!pwdNewVal;

  if (!emailChanged && !languageChanged && !pwdAny) return false;

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

  if (Object.keys(params).length === 0) {
    if (hasLanguageChanged()) {
      languageStore.setLanguage(selectedLanguage.value);
      showSettingsSnackbar.value = true;
      return;
    }
    generalServerError.value = t("modal.settings.no_changes");
    return;
  }

  try {
    const res = await userStore.updateUser(params);
    if (res && res.status === "ok") {
      showSettingsSnackbar.value = true;

      currentPassword.value = null;
      newPassword.value = null;
      passwordError.value = null;
      generalServerError.value = null;
    } else {
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
</style>
