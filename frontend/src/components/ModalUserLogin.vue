<template>
  <v-dialog v-model="dialog" max-width="350px">
    <v-card class="login">
      <v-toolbar color="primary" dark class="pl-6 pr-1 text-h6">
        {{ $t("user.login.title") }}
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
          clear-icon="mdi-close-circle-outline"
        />

        <p v-if="errorMessage.length > 0" class="text-uppercase font-weight-bold text-red">
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

        <a @click="showModalRegister = true" style="color: #1d3557; cursor: pointer">
          {{ $t("user.register.title") }}
        </a>
      </div>
      <ModalUserRegister v-model="showModalRegister" />
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, reactive, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import ModalUserRegister from "@/components/ModalUserRegister.vue";
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
const showModalRegister = ref(false);
const errorMessage = ref("");

const login = async () => {
  const status = await userStore.login(user);
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
      return t("user.login.rules.min");
    }
    if (value.length > 50) {
      return t("user.login.rules.max");
    }
    return true;
  }
  return t("field.required");
};

const disabled = computed(() => {
  if (Object.keys(user).length) {
    const total = Object.values(user).reduce((t, value) => t + (checkLength(value) === true), 0);
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

<style scoped>
.v-card.login .v-btn.register {
  min-width: auto !important;
  text-transform: capitalize;
  display: inline-block;
  letter-spacing: 0;
  font-size: 1rem;
  padding: 0 2px;
  height: 20px;
}

.v-card.login .v-btn.register:before,
.v-card.login .v-btn.register:hover:before,
.v-card.login .v-btn.register:focus:before {
  background-color: transparent;
}
</style>
