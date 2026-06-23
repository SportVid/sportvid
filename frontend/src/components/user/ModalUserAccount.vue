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
      <div class="d-flex justify-center ga-3 mt-6">
        <v-btn-toggle
          v-model="selectedLanguage"
          @update:model-value="languageStore.setLanguage(selectedLanguage)"
          color="primary"
          variant="outlined"
          divided
          mandatory
          density="compact"
        >
          <v-btn
            v-for="lang in languageStore.languages"
            :key="lang.code"
            :value="lang.code"
            size="small"
          >
            <v-avatar size="18">
              <v-img :src="lang.flag" contain />
            </v-avatar>
          </v-btn>
        </v-btn-toggle>

        <v-btn-toggle
          :model-value="themeStore.isDark ? 'dark' : 'light'"
          @update:model-value="
            (v) => {
              if (v !== undefined && (v === 'dark') !== themeStore.isDark) themeStore.toggle();
            }
          "
          color="primary"
          variant="outlined"
          divided
          mandatory
          density="compact"
        >
          <v-btn value="light" size="small"><v-icon>mdi-weather-sunny</v-icon></v-btn>
          <v-btn value="dark" size="small"><v-icon>mdi-weather-night</v-icon></v-btn>
        </v-btn-toggle>
      </div>

      <v-btn color="primary" variant="tonal" block class="mt-4" @click="userStore.openSettings()">
        {{ t("button.settings") }}
      </v-btn>
      <v-btn
        v-if="userStore.role === 'admin'"
        color="primary"
        variant="tonal"
        block
        class="mt-4"
        to="/admin"
      >
        {{ t("button.admin_panel") }}
      </v-btn>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { useUserStore } from "@/stores/user";
import { useLanguageStore } from "@/stores/languages";
import { useThemeStore } from "@/stores/theme";
const router = useRouter();
const { t } = useI18n();
const userStore = useUserStore();
const languageStore = useLanguageStore();
const themeStore = useThemeStore();

const selectedLanguage = ref(languageStore.currentLanguage);

const username = computed(() => userStore.username);
const initials = computed(() => (userStore.username ?? "").slice(0, 2).toUpperCase());

const logout = async () => {
  const loggedOut = await userStore.logout();
  if (loggedOut) {
    router.push({ name: "VideoView" });
  }
};
</script>
