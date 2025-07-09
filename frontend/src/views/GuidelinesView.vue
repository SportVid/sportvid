<template>
  <v-main>
    <v-container fluid>
      <v-card elevation="2" class="pa-4">
        <v-card-title class="text-h5">{{ $t("guidelines.title") }}</v-card-title>
        <v-card-text v-html="$t('guidelines.text')" />
      </v-card>
    </v-container>
  </v-main>
</template>
