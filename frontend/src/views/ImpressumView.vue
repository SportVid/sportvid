<template>
  <v-main>
    <v-container fluid>
      <v-card elevation="2" class="pa-4">
        <v-card-title class="text-h5">{{ $t("impressum.title") }}</v-card-title>
        <v-card-text class="impressum-content" v-html="$t('impressum.text')" />
        <v-card-text v-html="$t('impressum.last_updated')" />
      </v-card>
    </v-container>
  </v-main>
</template>

<style>
.impressum-content h3 {
  margin-top: 16px;
  margin-bottom: 4px;
}
.impressum-content h3:first-child {
  margin-top: 0;
}
.impressum-content p {
  margin-bottom: 8px;
}
</style>
