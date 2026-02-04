<template>
  <v-footer class="d-flex flex-column" color="primary" style="height: 90px; max-height: 90px">
    <v-col class="py-2">
      <div class="link-row">
        <div class="link-wrapper">
          <router-link to="/guidelines" class="router-link">
            {{ $t("guidelines.title") }}
          </router-link>
        </div>

        <v-divider vertical :thickness="2" inset></v-divider>

        <div class="link-wrapper">
          <router-link to="/terms-of-use" class="router-link">
            {{ $t("terms_of_use.title") }}
          </router-link>
        </div>
      </div>

      <div class="text-center mt-2">
        © {{ $t("plattform.title") }} – {{ new Date().getFullYear() }}
      </div>
    </v-col>
  </v-footer>
</template>

<style scoped>
.link-row {
  display: flex;
  justify-content: center;
  gap: 20px;
}

.link-wrapper {
  flex: 1;
  text-align: right;
}

.link-wrapper:last-of-type {
  text-align: left;
}

.router-link {
  color: white;
  text-decoration: none;
}

.router-link:hover {
  text-decoration: underline;
}
</style>
