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
        <div class="mb-4 d-flex justify-center" style="gap: 12px">
          <v-chip color="#666666">
            {{ $t("modal.bounding_box.edit.current_player_id") }}: {{ bbox[0] }}
          </v-chip>
          <v-chip color="#666666">
            {{ $t("modal.bounding_box.edit.current_team_id") }}: {{ bbox[1] }}
          </v-chip>
        </div>

        <v-text-field
          v-model="localPlayerId"
          :label="$t('modal.bounding_box.edit.new_player_id')"
          prepend-icon="mdi-account"
          variant="underlined"
          type="number"
          step="1"
        />

        <v-text-field
          v-model="localTeamId"
          :label="$t('modal.bounding_box.edit.new_team_id')"
          prepend-icon="mdi-account-group"
          variant="underlined"
        />

        <v-checkbox v-model="updateSamePlayerId" class="ml-n2">
          <template #label>
            <span style="margin-left: 8px">{{ $t("modal.bounding_box.edit.same_player_id") }}</span>
          </template>
        </v-checkbox>

        <v-checkbox v-model="updateSameTeamId" class="my-n6 ml-n2">
          <template #label>
            <span style="margin-left: 8px">{{ $t("modal.bounding_box.edit.same_team_id") }}</span>
          </template>
        </v-checkbox>

        <v-btn @click="update" :disabled="!localPlayerId || !localTeamId" class="mt-4">
          {{ $t("button.update") }}
        </v-btn>

        <v-btn @click="delete" :disabled="!localPlayerId || !localTeamId" class="mt-4 ml-4">
          {{ $t("button.delete") }}
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

const localPlayerId = ref("");
const localTeamId = ref("");
const updateSamePlayerId = ref(false);
const updateSameTeamId = ref(false);

watch(
  () => [props.bbox, dialog.value],
  ([bbox, open]) => {
    if (open && bbox) {
      localPlayerId.value = bbox[0];
      localTeamId.value = bbox[1];
    }
  },
  { immediate: true }
);

async function update() {
  emit("update", {
    player_id: localPlayerId.value,
    team_id: localTeamId.value,
    updateSamePlayerId: updateSamePlayerId.value,
    updateSameTeamId: updateSameTeamId.value,
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
