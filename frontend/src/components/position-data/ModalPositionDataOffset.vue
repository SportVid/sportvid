<template>
  <v-dialog v-model="dialog" width="700px">
    <v-card>
      <v-toolbar color="primary">
        <v-toolbar-title class="text-h6">
          {{ $t("modal.position_data.offset.title") }}
        </v-toolbar-title>
        <template #append>
          <v-btn icon="mdi-close" @click="dialog = false" variant="plain" color="grey" />
        </template>
      </v-toolbar>

      <v-card-text class="d-flex align-center">
        <v-text-field
          v-model="offset"
          :label="$t('modal.position_data.offset.label')"
          type="number"
          prepend-icon="mdi-timer"
          variant="underlined"
          class="mr-6"
        />

        <v-btn @click="applyOffset" :disabled="isNaN(offset)">
          {{ $t("button.update") }}
        </v-btn>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, watch } from "vue";
import { useTopViewStore } from "@/stores/top_view";

const topViewStore = useTopViewStore();

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
});
const emit = defineEmits(["update:modelValue"]);

const dialog = ref(props.modelValue);
watch(
  () => dialog.value,
  (value) => {
    emit("update:modelValue", value);
  }
);
watch(
  () => props.modelValue,
  (value) => {
    if (value) {
      dialog.value = true;
    }
  }
);

const offset = ref(topViewStore.currentTimeOffset);
const applyOffset = () => {
  topViewStore.currentTimeOffset = offset.value;
  dialog.value = false;
};
</script>
