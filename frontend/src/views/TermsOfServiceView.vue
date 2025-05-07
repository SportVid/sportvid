<template>
  <v-main>
    <v-container fluid>
      <v-card elevation="2" class="pa-4">
        <v-card-title class="text-h5">{{ $t("terms_of_service.title") }}</v-card-title>
        <v-card-text v-html="$t('terms_of_service.text')" />
      </v-card>
    </v-container>
  </v-main>
</template>
