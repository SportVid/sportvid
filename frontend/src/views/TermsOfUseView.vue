<template>
  <v-main>
    <v-container fluid>
      <v-card elevation="2" class="pa-4">
        <v-card-title class="text-h5">{{ $t("terms_of_use.title") }}</v-card-title>
        <v-card-text v-html="$t('terms_of_use.text')" />
        <v-card-text v-html="$t('terms_of_use.last_updated')" />
      </v-card>
    </v-container>
  </v-main>
</template>
