<template>
  <div>
    <v-menu location="bottom">
      <template #activator="{ props }">
        <v-btn v-bind="props" class="px-4 mr-1">
          <app-bar-icon size="x-large" class="mr-1">mdi-account-circle</app-bar-icon>
          {{ loggedIn ? username : $t("app_bar.user_menu") }}
        </v-btn>
      </template>

      <ModalUserAccount v-if="loggedIn" />

      <v-list v-else width="150px" class="pa-0 mr-n1" density="comfortable">
        <v-list-item @click="showModalLogin = true">
          <v-list-item-title class="text-center">{{ $t("user.login.title") }}</v-list-item-title>
        </v-list-item>
        <v-list-item @click="showModalRegister = true">
          <v-list-item-title class="text-center">{{ $t("user.register.title") }}</v-list-item-title>
        </v-list-item>
      </v-list>
    </v-menu>

    <ModalUserRegister
      v-if="showModalRegister"
      v-model="showModalRegister"
      @open-modal-user-login="handleOpenLogin"
    />
    <ModalUserLogin
      v-if="showModalLogin"
      v-model="showModalLogin"
      @open-modal-user-register="handleOpenRegister"
    />
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { useUserStore } from "@/stores/user";
import ModalUserLogin from "@/components/user/ModalUserLogin.vue";
import ModalUserRegister from "@/components/user/ModalUserRegister.vue";
import ModalUserAccount from "@/components/user/ModalUserAccount.vue";

const userStore = useUserStore();

const showModalLogin = ref(false);
const showModalRegister = ref(false);

const handleOpenLogin = () => {
  showModalLogin.value = true;
  showModalRegister.value = false;
};
const handleOpenRegister = () => {
  showModalRegister.value = true;
  showModalLogin.value = false;
};

const username = computed(() => userStore.username);
const loggedIn = computed(() => userStore.loggedIn);
</script>
