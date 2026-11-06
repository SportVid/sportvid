<template>
  <v-main>
    <v-container fluid>
      <v-card elevation="2" class="pa-4">
        <v-card-title class="text-h5">{{ $t("legal_notice.title") }}</v-card-title>
        <v-card-text class="legal-notice-content" v-html="$t('legal_notice.text')" />
        <v-card-text v-html="$t('legal_notice.last_updated')" />
      </v-card>
    </v-container>
  </v-main>
</template>

<style>
.legal-notice-content h3 {
  margin-top: 16px;
  margin-bottom: 4px;
}
.legal-notice-content h3:first-child {
  margin-top: 0;
}
.legal-notice-content p {
  margin-bottom: 8px;
}
</style>
