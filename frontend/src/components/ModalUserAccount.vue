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
      <h3 class="mt-4">{{ username }}</h3>
      <p class="my-2" style="max-width: 220px">
        {{ email }}
      </p>
      <p class="mb-4">
        <i>{{ joined }}</i>
      </p>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { computed } from "vue";
import { useRouter } from "vue-router";
import { useUserStore } from "@/stores/user";

const router = useRouter();
const userStore = useUserStore();

const username = computed(() => userStore.username);
const email = computed(() => userStore.email);
const date = computed(() => userStore.date);

const nDays = computed(() => {
  const dateObj = new Date(date.value);
  const diffInMs = new Date() - dateObj;
  return Math.round(diffInMs / (1000 * 60 * 60 * 24));
});
const joined = computed(() => `Joined ${nDays.value} days ago`);

const initials = computed(() => username.value.slice(0, 2));

const logout = async () => {
  const loggedOut = await userStore.logout();
  if (loggedOut) {
    router.push({ name: "VideoView" });
  }
};
</script>
