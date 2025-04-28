<template>
  <v-app>
    <AppBar />
    <router-view />
    <ModalError />
  </v-app>
</template>

<script setup>
import AppBar from "@/components/AppBar.vue";
import ModalError from "@/components/ModalError.vue";
</script>
