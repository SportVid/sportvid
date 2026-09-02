<template>
  <v-dialog v-model="dialog" :width="dialogWidth">
    <v-card class="register">
      <v-toolbar color="primary" dark class="pl-6 pr-1 text-h6">
        {{ $t("user.register.title") }}
        <v-spacer />
        <v-btn icon="mdi-close" @click="dialog = false" variant="plain" color="grey" />
      </v-toolbar>

      <v-card-text class="scrollable-content">
        <div v-if="showTerms" class="mb-n4">
          <h2 class="mb-2">{{ $t("terms_of_use.title") }}</h2>
          <div v-html="t('terms_of_use.text')" />
          <v-checkbox
            v-model="termsConfirmed"
            :label="t('terms_of_use.confirmation', { title: t('terms_of_use.title') })"
            class="mt-4"
          />
        </div>

        <form v-else @keyup.enter="register" class="mt-n2">
          <v-text-field
            v-model="user.name"
            :placeholder="$t('user.name')"
            prepend-icon="mdi-account"
            counter="50"
            persistent-counter
            :rules="[checkLength]"
            variant="underlined"
          />

          <v-text-field
            v-model="user.email"
            :placeholder="$t('user.email')"
            prepend-icon="mdi-email"
            counter="50"
            persistent-counter
            :rules="[checkLength]"
            variant="underlined"
          />

          <v-text-field
            v-model="user.password"
            :append-inner-icon="showPassword ? 'mdi-eye-outline' : 'mdi-eye-off-outline'"
            :placeholder="$t('user.password')"
            prepend-icon="mdi-lock"
            @click:append-inner="showPassword = !showPassword"
            :type="showPassword ? 'text' : 'password'"
            counter="50"
            persistent-counter
            :rules="[checkLength]"
            variant="underlined"
          />

          <p class="text-caption text-medium-emphasis mb-1 mt-4">
            {{ $t("user.experience_mode.heading") }}
          </p>
          <!-- One continuous border around toggle + sentence together (v-divider between the
               two rather than each getting its own border) so it reads as a single connected
               group instead of the sentence looking like a stray, unrelated box underneath. -->
          <v-sheet border rounded class="experience-mode-group">
            <v-btn-toggle
              v-model="user.experience_mode"
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
              :class="user.experience_mode === 'complex' ? 'text-right' : 'text-left'"
            >
              {{ $t(`user.experience_mode.${user.experience_mode}_sentence`) }}
            </div>
          </v-sheet>
        </form>

        <p
          v-if="errorMessage.length > 0"
          class="text-uppercase font-weight-bold text-red text-center mt-3 mb-n1"
        >
          Error: {{ errorMessage }}
        </p>
      </v-card-text>

      <v-card-actions>
        <v-btn
          v-if="showTerms"
          :disabled="!termsConfirmed"
          :class="{
            'text-white': !termsConfirmed || termsConfirmed,
            'bg-grey': !termsConfirmed,
            'bg-primary': termsConfirmed,
          }"
          @click="showTerms = false"
          rounded
          variant="tonal"
          style="width: 450px; display: block; margin: 0 auto"
          class="mt-2"
        >
          {{ t("button.continue") }}
        </v-btn>

        <v-btn
          v-else
          @click="register"
          :disabled="disabled"
          :class="{
            'text-white': disabled || !disabled,
            'bg-grey': disabled,
            'bg-primary': !disabled,
          }"
          class="px-6 mt-n4"
          block
          rounded
          depressed
          variant="tonal"
        >
          {{ $t("user.register.title") }}
        </v-btn>
      </v-card-actions>

      <div class="text-grey px-4 pb-4 pt-2" style="text-align: center">
        {{ $t("user.register.text") }}

        <a @click="openModalUserLogin" style="color: #1d3557; cursor: pointer">
          {{ $t("user.login.title") }}
        </a>
      </div>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useUserStore } from "@/stores/user";

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
});
const emit = defineEmits();

const { t } = useI18n();
const userStore = useUserStore();

const dialogWidth = computed(() => (showTerms.value ? 750 : 450));

const user = ref({
  name: "",
  password: "",
  email: "",
  // Preselected to "complex" -- the platform's current (unchanged) behavior -- rather than
  // nudging new users toward "simple" by default.
  experience_mode: "complex",
});
const dialog = ref(props.modelValue);
const showPassword = ref(false);
const errorMessage = ref("");

const openModalUserLogin = () => {
  emit("open-modal-user-login");
};

const register = async () => {
  const status = await userStore.register(user.value);
  if (status.status === "ok") {
    dialog.value = false;
  } else {
    errorMessage.value = status.message;
  }
};

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

const disabled = computed(() => {
  const total = ["name", "password", "email"].reduce(
    (t, field) => t + (checkLength(user.value[field]) === true),
    0
  );
  return total !== 3;
});

const showTerms = ref(true);
const termsConfirmed = ref(false);

watch(
  () => dialog.value,
  (newValue) => {
    emit("update:modelValue", newValue);
  }
);
watch(
  () => props.modelValue,
  (newValue) => {
    if (newValue) {
      dialog.value = true;
    }
  }
);
</script>

<style scoped>
.scrollable-content {
  max-height: 500px;
  overflow-y: auto;
}

/* Clips the toggle buttons' own square corners to the outer v-sheet's rounded ones, so the
   border reads as one seamless shape around the whole toggle+sentence group. */
.experience-mode-group {
  overflow: hidden;
}
</style>
