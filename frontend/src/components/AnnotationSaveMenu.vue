<template>
  <div>
    <v-menu min-width="175">
      <template v-slot:activator="{ props }">
        <v-btn size="small" v-bind="props" @click="showModalAnnotationSave = true">
          {{ $t("annotation_vis.save_annotation") }}
        </v-btn>
      </template>
    </v-menu>

    <ModalAnnotationSave v-model="showModalAnnotationSave" />
  </div>
</template>

<script setup>
import { ref } from "vue";
import ModalAnnotationSave from "@/components/ModalAnnotationSave.vue";

const showModalAnnotationSave = ref(false);
</script>
