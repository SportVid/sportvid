<template>
  <v-dialog v-model="dialog" width="500">
    <v-card>
      <v-toolbar color="primary">
        <v-toolbar-title class="text-h6">
          {{ $t("modal.bounding_box.edit.title") }}
        </v-toolbar-title>

        <template #append>
          <v-btn icon="mdi-close" @click="dialog = false" variant="plain" color="grey" />
        </template>
      </v-toolbar>

      <v-card-text class="pt-4">
        <v-text-field
          v-model="localRefId"
          label="ref_id"
          prepend-icon="mdi-pencil"
          variant="underlined"
          type="number"
          step="1"
        />

        <v-text-field
          v-model="localTeamId"
          label="team_id"
          prepend-icon="mdi-account-group"
          variant="underlined"
        />

        <v-checkbox v-model="updateAllRefId" class="ml-n2">
          <template #label>
            <span style="margin-left: 8px">{{ $t("modal.bounding_box.edit.all_ref_id") }}</span>
          </template>
        </v-checkbox>

        <v-checkbox v-model="updateAllTeamId" class="my-n6 ml-n2">
          <template #label>
            <span style="margin-left: 8px">{{ $t("modal.bounding_box.edit.all_team_id") }}</span>
          </template>
        </v-checkbox>

        <v-btn @click="update" :disabled="!localRefId || !localTeamId" class="mt-4">
          {{ $t("button.update") }}
        </v-btn>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, watch } from "vue";

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  bbox: Object,
});
const emit = defineEmits();

const dialog = ref(props.modelValue);

const localRefId = ref("");
const localTeamId = ref("");
const updateAllRefId = ref(false);
const updateAllTeamId = ref(false);

watch(
  () => [props.bbox, dialog.value],
  ([bbox, open]) => {
    if (open && bbox) {
      localRefId.value = bbox.ref_id ?? "";
      localTeamId.value = bbox.team_id ?? "";
    }
  },
  { immediate: true }
);

async function update() {
  emit("update", {
    ref_id: localRefId.value,
    team_id: localTeamId.value,
    updateAllRefId: updateAllRefId.value,
    updateAllTeamId: updateAllTeamId.value,
  });
  dialog.value = false;
}

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
</script>
