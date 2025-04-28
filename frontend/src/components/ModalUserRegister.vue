<template>
  <v-dialog v-model="dialog" width="450px">
    <v-card class="register">
      <v-toolbar color="primary" dark class="pl-6 pr-1 text-h6">
        {{ $t("user.register.title") }}
        <v-spacer />
        <v-btn icon="mdi-close" @click="dialog = false" variant="plain" color="grey" />
      </v-toolbar>

      <v-card-text class="mt-n2">
        <form @keyup.enter="register">
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
        </form>

        <p
          v-if="errorMessage.length > 0"
          class="text-uppercase font-weight-bold text-red text-center mt-3 mb-n1"
        >
          Error: {{ errorMessage }}
        </p>
      </v-card-text>

      <v-card-actions class="px-6 mt-n4">
        <v-btn
          @click="register"
          :disabled="disabled"
          :class="{
            'text-white': disabled || !disabled,
            'bg-grey': disabled,
            'bg-primary': !disabled,
          }"
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

const user = ref({
  name: "",
  password: "",
  email: "",
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
  const total = Object.keys(user.value).length
    ? Object.values(user.value).reduce((t, value) => t + (checkLength(value) === true), 0)
    : 0;
  return total !== 3;
});

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
