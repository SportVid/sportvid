<template>
  <v-footer
    class="text-center d-flex flex-column"
    color="primary"
    style="height: auto; max-height: 114px; overflow: hidden"
  >
    <router-link to="/terms-of-service" class="py-2 terms-of-service-link">
      Terms of Service
    </router-link>
    <v-divider class="my-2" thickness="2" width="50px"></v-divider>
    <div class="py-2">{{ new Date().getFullYear() }} — <strong>SportVid</strong></div>
  </v-footer>
</template>

<style scoped>
.terms-of-service-link {
  color: white;
  text-decoration: none;
}

.terms-of-service-link:hover {
  text-decoration: underline;
}
</style>
