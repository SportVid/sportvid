<template>
  <v-card>
    <v-toolbar color="primary" dark>Annotate Timeline Segment</v-toolbar>
    <v-card-text>
      <form>
        <v-text-field v-model="annotation.label" :counter="120" label="Label" required />

        <v-btn class="mr-4" :disabled="disabled" @click="annotateSegment"> Upload </v-btn>
        <v-btn @click="dialog = false">Close</v-btn>
      </form>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref } from "vue";

const annotation = ref({ label: "" });
const dialog = ref(false);
const disabled = ref(false);

const annotateSegment = () => {
  console.log(annotation.value);
  dialog.value = false;
};
</script>
