<template>
  <v-app>
    <AppBar />
    <router-view />
    <ModalError />
    <AppFooter />
  </v-app>
</template>

<script setup>
import AppBar from "@/components/AppBar.vue";
import ModalError from "@/components/ModalError.vue";
import AppFooter from "./components/AppFooter.vue";
</script>
