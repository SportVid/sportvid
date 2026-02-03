<template>
  <v-card width="250px" class="mr-n1">
    <v-container class="d-flex justify-end" height="30px">
      <v-btn
        :title="$t('user.logout.title')"
        size="large"
        class="mt-n2 mr-n2"
        @click="logout"
        icon="mdi-logout-variant"
        variant="text"
        color="grey"
        density="compact"
      />
    </v-container>
    <v-card-text class="text-center mt-n2">
      <v-avatar size="large" :style="{ backgroundColor: '#457B9D80' }">
        <span class="text-white text-h5">{{ initials }}</span>
      </v-avatar>
      <v-btn color="primary" variant="tonal" block class="mt-6" @click="userStore.openSettings()">{{
        t("button.settings")
      }}</v-btn>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { useUserStore } from "@/stores/user";
const router = useRouter();
const { t } = useI18n();
const userStore = useUserStore();

const username = computed(() => userStore.username);
const initials = computed(() => username.value.slice(0, 2));

const logout = async () => {
  const loggedOut = await userStore.logout();
  if (loggedOut) {
    router.push({ name: "VideoView" });
  }
};
</script>
