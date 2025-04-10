<template>
  <v-dialog v-model="dialog" max-width="350px">
    <v-card class="register">
      <v-toolbar color="primary" dark class="pl-6 pr-1 text-h6">
        {{ $t("user.register.title") }}
        <v-spacer />
        <v-btn icon="mdi-close" @click="dialog = false" variant="plain" color="grey" />
      </v-toolbar>

      <v-card-text class="mt-n2">
        <v-text-field
          v-model="user.name"
          :placeholder="$t('user.name')"
          prepend-icon="mdi-account"
          counter="50"
          persistent-counter
          :rules="[checkLength]"
          variant="underlined"
          clearable
          clear-icon="mdi-close-circle-outline"
        />

        <v-text-field
          v-model="user.email"
          :placeholder="$t('user.email')"
          prepend-icon="mdi-email"
          counter="50"
          persistent-counter
          :rules="[checkLength]"
          variant="underlined"
          clearable
          clear-icon="mdi-close-circle-outline"
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
          clearable
        />

        <p v-if="errorMessage.length > 0" class="text-uppercase font-weight-bold text-red">
          Error: {{ errorMessage }}
        </p>
      </v-card-text>

      <v-card-actions class="px-6 mt-n4 mb-2">
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
    </v-card>
  </v-dialog>
</template>

<script setup>
import { reactive, ref, computed, watch } from "vue";
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

const user = reactive({});
const dialog = ref(props.modelValue);
const showPassword = ref(false);
const errorMessage = ref("");

const register = async () => {
  const status = await userStore.register(user);
  if (status.status === "ok") {
    dialog.value = false;
    errorMessage.value = "";
  } else {
    errorMessage.value = status.message;
  }
};

const checkLength = (value) => {
  if (value) {
    if (value.length < 5) {
      return t("user.register.rules.min");
    }
    if (value.length > 50) {
      return t("user.register.rules.max");
    }
    return true;
  }
  return t("field.required");
};

const disabled = computed(() => {
  const total = Object.keys(user).length
    ? Object.values(user).reduce((t, value) => t + (checkLength(value) === true), 0)
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

<style>
.v-card.register .v-btn.login {
  min-width: auto !important;
  text-transform: capitalize;
  display: inline-block;
  letter-spacing: 0;
  font-size: 1rem;
  padding: 0 2px;
  height: 20px;
}

.v-card.register .v-btn.login:before,
.v-card.register .v-btn.login:hover:before,
.v-card.register .v-btn.login:focus:before {
  background-color: transparent;
}
</style>
