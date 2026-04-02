<template>
  <v-app>
    <AppBar />
    <router-view />
    <ModalError />
    <AppFooter />
  </v-app>
</template>

<script setup>
import AppBar from "@/components/app/app-bar/AppBar.vue";
import ModalError from "@/components/app/ModalError.vue";
import AppFooter from "./components/app/AppFooter.vue";
</script>
