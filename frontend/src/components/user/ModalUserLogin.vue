<template>
  <v-dialog v-model="dialog" width="450px">
    <v-card class="login">
      <v-toolbar color="primary">
        <v-toolbar-title class="text-h6">
          {{ $t("user.login.title") }}
        </v-toolbar-title>

        <template #append>
          <v-btn icon="mdi-close" @click="dialog = false" variant="plain" color="grey" />
        </template>
      </v-toolbar>

      <v-card-text class="mt-n2">
        <form @keyup.enter="login">
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

      <v-card-actions class="px-6 mt-n2">
        <v-btn
          @click="login"
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
          {{ $t("user.login.title") }}
        </v-btn>
      </v-card-actions>

      <div class="text-grey px-4 pb-4 pt-2" style="text-align: center">
        {{ $t("user.login.text") }}

        <a @click="openModalUserRegister" style="color: #1d3557; cursor: pointer">
          {{ $t("user.register.title") }}
        </a>
      </div>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useUserStore } from "@/stores/user";
import { log1pDependencies } from "mathjs";

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
});
const dialog = ref(props.modelValue);
const showPassword = ref(false);
const errorMessage = ref("");

const openModalUserRegister = () => {
  emit("open-modal-user-register");
};

const login = async () => {
  const status = await userStore.login(user.value);
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
    return t("user.login.rules.min");
  }
  if (value.length > 50) {
    return t("user.login.rules.max");
  }
  return true;
};

const disabled = computed(() => {
  if (Object.keys(user.value).length) {
    const total = Object.values(user.value).reduce(
      (t, value) => t + (checkLength(value) === true),
      0
    );
    return total !== 2;
  }
  return true;
});

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
</script>
