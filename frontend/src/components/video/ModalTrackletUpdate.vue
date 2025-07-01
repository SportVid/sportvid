<!-- filepath: frontend/src/components/EditBBoxFieldModal.vue -->
<template>
  <v-dialog v-model="dialog" width="400">
    <v-card>
      <v-toolbar color="primary">
        <v-toolbar-title class="text-h6">
          {{ $t("modal.bbox.edit.title", { field: fieldLabel }) }}
        </v-toolbar-title>
        <template #append>
          <v-btn icon="mdi-close" @click="close" variant="plain" color="grey" />
        </template>
      </v-toolbar>
      <v-card-text class="pt-4 d-flex align-center">
        <v-text-field
          v-model="editValue"
          :label="fieldLabel"
          prepend-icon="mdi-pencil"
          variant="underlined"
          class="mr-6"
        />
        <v-btn @click="submit" :disabled="isSubmitting || !editValue">
          {{ $t("button.save") }}
        </v-btn>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, watch, computed } from "vue";

const props = defineProps({
  modelValue: Boolean,
  bbox: Object, // Die aktuelle BBox
  field: String, // Das zu bearbeitende Feld, z.B. "ref_id" oder "team_id"
});
const emit = defineEmits(["update:modelValue", "save"]);

const dialog = computed({
  get: () => props.modelValue,
  set: (val) => emit("update:modelValue", val),
});

const editValue = ref("");
const isSubmitting = ref(false);

const fieldLabel = computed(() => {
  // Optional: Übersetzung oder Formatierung des Feldnamens
  if (props.field === "ref_id") return "ref_id";
  if (props.field === "team_id") return "team_id";
  return props.field;
});

watch(
  () => [props.bbox, props.field, dialog.value],
  ([bbox, field, open]) => {
    if (open && bbox && field) {
      editValue.value = bbox[field] ?? "";
    }
  },
  { immediate: true }
);

function close() {
  emit("update:modelValue", false);
}

async function submit() {
  if (isSubmitting.value) return;
  isSubmitting.value = true;
  emit("save", { field: props.field, value: editValue.value });
  isSubmitting.value = false;
  close();
}
</script>
