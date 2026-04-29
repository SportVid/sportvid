<template>
  <v-main>
    <v-container fluid>
      <v-alert
        type="info"
        variant="tonal"
        class="mb-4"
        :icon="userStore.loggedIn ? 'mdi-school' : 'mdi-information-outline'"
      >
        <span v-if="userStore.loggedIn">
          {{ $t("guidelines.tutorial_hint_loggedin") }}
          <v-btn variant="text" class="ml-1" @click="tutorialStore.openTutorialModal = true">
            <v-icon class="mr-1">mdi-school</v-icon>
            {{ $t("guidelines.tutorial_hint_btn") }}
          </v-btn>
        </span>
        <span v-else v-html="$t('guidelines.tutorial_hint_loggedout')" />
      </v-alert>

      <v-card elevation="2" class="pa-4">
        <v-card-title class="text-h5">{{ $t("guidelines.title") }}</v-card-title>
        <v-card-text>
          <div class="guidelines-content" v-html="$t('guidelines.text')" />
        </v-card-text>
      </v-card>
    </v-container>
  </v-main>
</template>

<script setup>
import { useUserStore } from "@/stores/user";
import { useTutorialStore } from "@/stores/tutorial";

const userStore = useUserStore();
const tutorialStore = useTutorialStore();
</script>

<style>
.guidelines-content ol {
  margin-left: 20px;
  line-height: 1.7;
}
.guidelines-content ol ol {
  margin-top: 4px;
  margin-bottom: 4px;
}
.guidelines-content li {
  margin-bottom: 4px;
}
</style>
