<template>
  <v-list min-width="250">
    <v-container class="d-flex justify-end align-start">
      <v-btn
        :title="$t('user.logout.title')"
        class="mr-n3 mt-n5 mb-n5"
        @click="logout"
        icon="mdi-logout-variant"
        variant="text"
        color="grey"
      />
    </v-container>

    <v-list-item class="account justify-center pb-6 pl-6 pr-6 pt-0 mt-n2">
      <div class="mx-auto text-center">
        <v-avatar size="large" :style="{ backgroundColor: `#457B9D80` }">
          <span class="text-white text-h5">{{ initials }}</span>
        </v-avatar>

        <h3 class="mt-4">{{ username }}</h3>
        <p class="text-caption clip mt-2 mb-0" style="max-width: 200px">
          {{ email }}
        </p>
        <p class="text-caption mb-0">
          <i>{{ joined }}</i>
        </p>
      </div>
    </v-list-item>
  </v-list>
</template>

<script setup>
import { computed } from "vue";
import { useRouter } from "vue-router";
import { useUserStore } from "@/stores/user";
import { repPlace } from "../plugins/helpers";
import { useI18n } from "vue-i18n";

const { t } = useI18n();
const userStore = useUserStore();
const router = useRouter();

const username = computed(() => userStore.username);
const email = computed(() => userStore.email);
const date = computed(() => userStore.date);

const nDays = computed(() => {
  const dateObj = new Date(date.value);
  const diffInMs = new Date() - dateObj;
  return Math.round(diffInMs / (1000 * 60 * 60 * 24));
});

const joined = computed(() => {
  const text = "Joined {n_days} days ago";
  return repPlace({ n_days: nDays.value }, text);
});

const initials = computed(() => username.value.slice(0, 2));

const logout = async () => {
  const loggedOut = await userStore.logout();
  if (loggedOut) {
    router.push({ name: "VideoView" });
  }
};
</script>

<style>
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
