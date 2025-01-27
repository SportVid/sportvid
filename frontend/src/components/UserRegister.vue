<template>
  <v-dialog v-model="dialog" max-width="350px">
    <v-card class="register">
      <v-card-title class="d-flex justify-space-between align-center mb-n6">
        <span class="ms-2 text-primary">{{ $t("user.register.title") }}</span>

        <v-btn 
          icon 
          @click="dialog = false" 
          variant="text" 
          class="mr-n2" 
          color="grey"
        >
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-card-text>
        <v-text-field
          v-model="user.name"
          :placeholder="$t('user.name')"
          prepend-icon="mdi-account"
          counter="50"
          persistent-counter
          :rules="[checkLength]"
          variant="underlined"
          clearable
        ></v-text-field>

        <v-text-field
          v-model="user.email"
          :placeholder="$t('user.email')"
          prepend-icon="mdi-email"
          counter="50"
          persistent-counter
          :rules="[checkLength]"
          variant="underlined"
          clearable
        ></v-text-field>

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
        ></v-text-field>
        <p 
          v-if="errorMessage.length>0" 
          class="text-uppercase font-weight-bold text-red"
        >
          Error: {{ errorMessage }}
        </p>
      </v-card-text>

      <v-card-actions class="px-6 mt-n2">
        <v-btn
          @click="register"
          :disabled="disabled"
          :class="{
            'text-white': disabled,
            'bg-grey': disabled,
            'text-white': !disabled,
            'bg-accent': !disabled,
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

        <a @click="showModalLogin = true" style="color: #1D3557; cursor: pointer">
          {{ $t("user.login.title") }}
        </a>

        <UserLogin v-model="showModalLogin">
          <activator />
        </UserLogin>
      </div>
    </v-card>
  </v-dialog>
</template>

<script>
import { reactive, ref, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import UserLogin from "@/components/UserLogin.vue";
import { useUserStore } from "@/stores/user";

export default {
  props: {
    modelValue: {
      type: Boolean,
      default: false,
    },
  },
  components: {
    UserLogin,
  },
  setup(props, { emit }) {
    const { t } = useI18n();
    const userStore = useUserStore();

    const user = reactive({});
    const dialog = ref(props.modelValue);
    const showPassword = ref(false);
    const showModalLogin = ref(false);
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

    return {
      user,
      dialog,
      showPassword,
      showModalLogin,
      errorMessage,
      register,
      checkLength,
      disabled,
    };
  },
};
</script>
