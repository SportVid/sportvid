<template>
  <div>
    <v-menu location="bottom right" offset-y>
      <template v-slot:activator="{ props }">
        <v-btn v-bind="props" class="pl-4 pr-4 mr-4">
          <v-icon size="x-large" color="primary" class="mr-1">mdi-account-circle</v-icon>
          <span v-if="loggedIn" color="accent">{{ username }}</span>
          <span v-else>{{ $t("app_bar.user_menu") }}</span>
        </v-btn>
      </template>

      <ModalUserAccount v-if="loggedIn" />

      <v-list v-else min-width="175" class="pa-0">
        <v-list-item @click="showModalLogin = true">
          <v-list-item-title>{{ $t("user.login.title") }}</v-list-item-title>
        </v-list-item>
        <v-list-item @click="showModalRegister = true">
          <v-list-item-title>{{ $t("user.register.title") }}</v-list-item-title>
        </v-list-item>
      </v-list>
    </v-menu>

    <ModalUserRegister v-if="showModalRegister" v-model="showModalRegister" />
    <ModalUserLogin v-if="showModalLogin" v-model="showModalLogin" />
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { useUserStore } from "@/stores/user";
import ModalUserLogin from "@/components/ModalUserLogin.vue";
import ModalUserRegister from "@/components/ModalUserRegister.vue";
import ModalUserAccount from "@/components/ModalUserAccount.vue";

const showModalLogin = ref(false);
const showModalRegister = ref(false);

const userStore = useUserStore();

const username = computed(() => userStore.username);
const loggedIn = computed(() => userStore.loggedIn);
</script>

<style scoped>
.v-list-item__content.account {
  min-width: 250px;
  letter-spacing: 0.0892857143em;
  border-bottom: 1px solid #f5f5f5;
}

.v-menu__content .account .v-btn:not(.accent) {
  justify-content: center;
}

.v-application .v-avatar.secondary {
  background-color: rgba(69, 123, 157, 0.54) !important;
  border-color: rgba(69, 123, 157, 0.54) !important;
}

.account {
  background-color: rgb(255, 255, 255) !important;
}
</style>
