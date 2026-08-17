<template>
  <v-dialog v-model="dialog" width="600">
    <v-card>
      <v-toolbar color="primary">
        <v-toolbar-title class="text-h6">
          {{ $t("modal.bounding_box.edit.title") }}
        </v-toolbar-title>

        <template #append>
          <v-btn icon="mdi-close" @click="dialog = false" variant="plain" color="grey" />
        </template>
      </v-toolbar>

      <v-card-text class="pt-4" style="overflow-y: auto">
        <v-row justify="center" class="mt-0 mb-1">
          <v-tabs v-model="selectedMode" fixed-tabs slider-color="primary">
            <v-tab v-for="mode in BboxUpdateModes" :key="mode.id" :value="mode.id">
              {{ mode.name }}
            </v-tab>
          </v-tabs>
        </v-row>

        <v-row>
          <v-col>
            <v-tabs-window v-model="selectedMode">
              <v-tabs-window-item v-for="mode in BboxUpdateModes" :key="mode.id" :value="mode.id">
                <v-alert
                  color="primary"
                  density="compact"
                  variant="tonal"
                  icon="mdi-alert-circle-outline"
                  style="font-size: 0.9rem"
                >
                  {{
                    mode.id === "bbox"
                      ? $t("modal.bounding_box.edit.modes.info_bbox")
                      : mode.id === "allPlayer"
                      ? $t("modal.bounding_box.edit.modes.info_all_player")
                      : mode.id === "allTeam"
                      ? $t("modal.bounding_box.edit.modes.info_all_team")
                      : ""
                  }}
                </v-alert>

                <div class="mt-4 mb-4 d-flex justify-center" style="gap: 12px">
                  <v-chip v-if="mode.id === 'bbox'" color="#666666">
                    {{ $t("modal.bounding_box.edit.current_box_id") }}: {{ bboxData.bboxId }}
                  </v-chip>
                  <v-chip v-if="mode.id === 'bbox'" color="#666666">
                    {{ $t("modal.bounding_box.edit.current_player_id") }}: {{ bboxData.playerId }}
                  </v-chip>

                  <v-menu
                    v-if="mode.id === 'allPlayer'"
                    transition="scale-transition"
                    location="bottom center"
                  >
                    <template #activator="{ props }">
                      <v-chip
                        v-bind="props"
                        color="#666666"
                        class="cursor-pointer"
                        style="border: 1px solid rgba(var(--v-theme-primary))"
                      >
                        {{ $t("modal.bounding_box.edit.current_player_id") }}:
                        {{ bboxData.playerId }}
                      </v-chip>
                    </template>

                    <div class="player-team-selector mt-2 pa-1">
                      <div
                        v-for="playerId in playerOptions"
                        :key="playerId"
                        class="dot"
                        :style="{
                          backgroundColor: toRgb(playerColors[playerId], 0.7),
                          color: getContrastColor(playerColors[playerId], 0.7),
                          borderColor: toRgb(playerColors[playerId], 0.7),
                        }"
                        @click="bboxData.playerId = playerId"
                      >
                        {{ playerId }}
                      </div>
                    </div>
                  </v-menu>

                  <v-chip v-if="mode.id === 'bbox' || mode.id === 'allPlayer'" color="#666666">
                    {{ $t("modal.bounding_box.edit.current_team_id") }}:
                    {{ bboxData.teamId?.id ?? bboxData.teamId }}
                  </v-chip>

                  <v-menu v-if="mode.id === 'allTeam'" transition="scale-transition">
                    <template #activator="{ props }">
                      <v-chip
                        v-bind="props"
                        color="#666666"
                        class="cursor-pointer"
                        style="border: 1px solid rgba(var(--v-theme-primary))"
                      >
                        {{ $t("modal.bounding_box.edit.current_team_id") }}:
                        {{ bboxData.teamId?.id ?? bboxData.teamId }}
                      </v-chip>
                    </template>
                    <div class="player-team-selector mt-2 pa-1">
                      <div
                        v-for="teamId in teamOptions.filter((t) => !t.isNew)"
                        :key="teamId.id"
                        class="dot"
                        :style="{
                          backgroundColor: toRgb(visualizationStore.getTeamColor(teamId.id), 0.7),
                          color: getContrastColor(visualizationStore.getTeamColor(teamId.id), 0.7),
                        }"
                        @click="bboxData.teamId = teamId"
                      >
                        {{ teamId.id }}
                      </div>
                    </div>
                  </v-menu>
                </div>

                <template v-if="mode.id === 'bbox'">
                  <v-text-field
                    v-model="bboxData.newPlayerId"
                    :label="$t('modal.bounding_box.edit.new_player_id')"
                    prepend-icon="mdi-account"
                    variant="underlined"
                    type="number"
                    step="1"
                    min="0"
                    max="999"
                    :rules="[checkPlayerId]"
                  />

                  <v-select
                    v-model="bboxData.newTeamId"
                    :items="teamOptions"
                    item-title="label"
                    item-value="id"
                    :label="$t('modal.bounding_box.edit.new_team_id')"
                    prepend-icon="mdi-account-group"
                    variant="underlined"
                    class="mt-3"
                    :rules="[checkTeamId]"
                  />
                </template>

                <template v-if="mode.id === 'allPlayer'">
                  <v-text-field
                    v-model="bboxData.newPlayerId"
                    :label="$t('modal.bounding_box.edit.new_player_id')"
                    prepend-icon="mdi-account"
                    variant="underlined"
                    type="number"
                    step="1"
                    min="0"
                    max="999"
                    :rules="[checkPlayerId]"
                  />

                  <v-select
                    v-model="bboxData.newTeamId"
                    :items="teamOptions"
                    item-title="label"
                    item-value="id"
                    :label="$t('modal.bounding_box.edit.new_team_id')"
                    prepend-icon="mdi-account-group"
                    variant="underlined"
                    class="mt-3"
                    :rules="[checkTeamId]"
                  />
                </template>

                <template v-if="mode.id === 'allTeam'">
                  <v-select
                    v-model="bboxData.newTeamId"
                    :items="teamOptions"
                    item-title="label"
                    item-value="id"
                    :label="$t('modal.bounding_box.edit.new_team_id')"
                    prepend-icon="mdi-account-group"
                    variant="underlined"
                    class="mt-3"
                    :rules="[checkTeamId]"
                  />
                </template>
              </v-tabs-window-item>
            </v-tabs-window>
          </v-col>
        </v-row>

        <v-btn
          @click="updateBboxData"
          :disabled="bboxData.newPlayerId == null || bboxData.newTeamId == null"
          class="mt-4"
        >
          {{ $t("button.update") }}
        </v-btn>

        <v-btn
          @click="deleteBboxData"
          :disabled="bboxData.newPlayerId == null || bboxData.newTeamId == null"
          class="mt-4 ml-4"
        >
          {{ $t("button.delete") }}
        </v-btn>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useTopViewStore, BBOX_SOURCE_RUN_IDX } from "@/stores/top_view";
import { useBboxesStore } from "@/stores/bboxes";
import { usePlayerStore } from "@/stores/player";
import { useVisualizationStore } from "@/stores/visualization";
import { toRgb, getContrastColor } from "@/plugins/helpers";

const topViewStore = useTopViewStore();
const bboxesStore = useBboxesStore();
const playerStore = usePlayerStore();
const visualizationStore = useVisualizationStore();

const { t } = useI18n();

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  bbox: Object,
});
const emit = defineEmits();

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

const bboxData = ref({});
watch(
  () => [props.bbox, dialog.value],
  ([bboxEntry, open]) => {
    if (open && bboxEntry) {
      const bbox = bboxEntry.box;
      // Route edits/deletes to whichever plugin run this bbox was physically loaded from.
      // Not derived from team_id: team_id is a mutable field a previous edit may already
      // have reassigned across the ball/player boundary, while the entry's physical file
      // never changes -- see BBOX_SOURCE_RUN_IDX in top_view.js.
      bboxData.value.bytetrackRunId = bbox[BBOX_SOURCE_RUN_IDX] ?? bboxesStore.bboxPluginRunId;
      bboxData.value.bboxId = bboxEntry.bboxId;
      bboxData.value.playerId = bbox[0];
      bboxData.value.teamId = bbox[1];
      bboxData.value.newPlayerId = bbox[0];
      bboxData.value.newTeamId = bbox[1];
      bboxData.value.applyAllPlayerId = false;
      bboxData.value.applyAllTeamId = false;
    }
  },
  { immediate: true }
);

const selectedMode = ref("bbox");
// "allPlayer" (rename all boxes with a given player id) is hidden once a ReID run is merged:
// a single reid identity can correspond to several different original track_ids over time,
// so a global rename by id is ambiguous (see bboxesStore.translatePlayerId).
const BboxUpdateModes = computed(() => [
  { id: "bbox", name: t("modal.bounding_box.edit.modes.bbox") },
  ...(bboxesStore.bboxReidMapping
    ? []
    : [{ id: "allPlayer", name: t("modal.bounding_box.edit.modes.all_player") }]),
  { id: "allTeam", name: t("modal.bounding_box.edit.modes.all_team") },
]);

const playerOptions = computed(() => {
  return topViewStore.precomputedPlayerList.map((p) => p.playerId);
});
const playerColors = computed(() => {
  const map = {};
  for (const p of topViewStore.precomputedPlayerList) {
    map[p.playerId] = visualizationStore.getTeamColor(p.teamId);
  }
  return map;
});
const teamOptions = computed(() => {
  const existing = [...new Set(topViewStore.precomputedPlayerList.map((p) => p.teamId))]
    .filter((id) => id >= 3)
    .sort((a, b) => a - b);

  let nextId = 3;
  while (existing.includes(nextId) && nextId <= 10) {
    nextId++;
  }

  const options = [
    { id: -1, label: t("modal.bounding_box.edit.team.unknown"), isNew: false },
    { id: 0, label: t("modal.bounding_box.edit.team.ball"), isNew: false },
    { id: 1, label: t("modal.bounding_box.edit.team.rest"), isNew: false },
    { id: 2, label: t("modal.bounding_box.edit.team.referee"), isNew: false },
    ...existing.map((id) => ({
      id,
      label: t("modal.bounding_box.edit.team.team", { id: id }),
      isNew: false,
    })),
  ];

  if (nextId <= 12) {
    options.push({
      id: nextId,
      label: t("modal.bounding_box.edit.team.new_team", { id: nextId }),
      isNew: true,
    });
  }

  return options;
});

const checkPlayerId = (value) => {
  const frame = topViewStore.getFrameAt(playerStore.currentTime);
  const playerIds = frame.map((p) => p[0]);

  if (value === null || value === undefined || value === "") {
    return t("field.required");
  }
  if (value < 0) {
    return t("modal.bounding_box.edit.rules.player_min");
  }
  if (value > 999) {
    return t("modal.bounding_box.edit.rules.player_max");
  }
  if (playerIds.includes(Number(value)) && Number(value) !== bboxData.value.playerId) {
    return t("modal.bounding_box.edit.rules.player_duplicate");
  }
  return true;
};

const checkTeamId = (value) => {
  if (value === null || value === undefined || value === "") {
    return t("field.required");
  }
  return true;
};

const updateBboxData = async () => {
  if (selectedMode.value === "allPlayer") bboxData.value.applyAllPlayerId = true;
  if (selectedMode.value === "allTeam") bboxData.value.applyAllTeamId = true;

  await bboxesStore.updateBboxData(bboxData.value);
  dialog.value = false;
};

const deleteBboxData = async () => {
  if (selectedMode.value === "allPlayer") bboxData.value.applyAllPlayerId = true;
  if (selectedMode.value === "allTeam") bboxData.value.applyAllTeamId = true;

  await bboxesStore.deleteBboxData(bboxData.value);
  dialog.value = false;
};
</script>

<style scoped>
.player-team-selector {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  justify-content: center;
  margin: 12px 0 8px 0;
  background-color: white;
  border-radius: 8px;
  border: 1px solid #222;
}

.dot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 0.8rem;
  border: 1px solid transparent;
  transition: all 0.2s;
}
.dot:hover {
  transform: scale(1.1);
}
</style>
