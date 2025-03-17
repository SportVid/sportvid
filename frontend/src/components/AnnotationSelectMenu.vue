<template>
  <div>
    <v-menu min-width="175">
      <template v-slot:activator="{ props }">
        <v-btn size="small" v-bind="props" @click="showModalAnnotationSelect = true">
          {{ $t("annotation_vis.select_annotation") }}
        </v-btn>
      </template>
    </v-menu>

    <ModalAnnotationSelect v-model="showModalAnnotationSelect" />
  </div>
</template>

<script setup>
import { ref } from "vue";
import ModalAnnotationSelect from "@/components/ModalAnnotationSelect.vue";

const showModalAnnotationSelect = ref(false);
</script>
