<template>
  <div>
    <v-menu min-width="175">
      <template v-slot:activator="{ props }">
        <v-btn size="small" v-bind="props" @click="showModalAnnotation = true">
          {{ $t("annotation_vis.select_annotation") }}
        </v-btn>
      </template>
    </v-menu>

    <ModalAnnotation v-model="showModalAnnotation" />
  </div>
</template>

<script setup>
import { ref } from "vue";
import ModalAnnotation from "@/components/ModalAnnotation.vue";

const showModalAnnotation = ref(false);
</script>
