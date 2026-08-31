<template>
  <div class="identity-panel">
    <div class="panel-heading">{{ $t("annotation_tool.identity.title") }}</div>

    <div v-if="!box" class="panel-empty text-medium-emphasis">
      {{ $t("annotation_tool.identity.no_selection") }}
    </div>

    <template v-else>
      <div class="d-flex flex-wrap mb-3" style="gap: 6px">
        <v-chip size="small" color="#666666">
          {{ $t("modal.bounding_box.edit.current_box_id") }}: {{ bboxId }}
        </v-chip>
        <v-chip size="small" :color="currentColor">
          {{ $t("modal.bounding_box.edit.current_player_id") }}: {{ box[0] }}
        </v-chip>
        <v-chip size="small" color="#666666">
          {{ $t("modal.bounding_box.edit.current_team_id") }}: {{ box[1] }}
        </v-chip>
      </div>

      <div class="panel-subheading">{{ $t("annotation_tool.identity.scope") }}</div>
      <v-btn-toggle
        v-model="selectedMode"
        mandatory
        density="compact"
        color="primary"
        variant="outlined"
        class="mb-2 scope-toggle"
      >
        <v-btn v-for="mode in updateModes" :key="mode.id" :value="mode.id" size="small">
          {{ mode.name }}
        </v-btn>
      </v-btn-toggle>

      <v-alert
        color="primary"
        density="compact"
        variant="tonal"
        icon="mdi-alert-circle-outline"
        class="mb-3"
        style="font-size: 0.8rem"
      >
        {{ scopeHint }}
      </v-alert>

      <v-text-field
        v-if="selectedMode !== 'allTeam'"
        v-model="newPlayerId"
        :label="$t('modal.bounding_box.edit.new_player_id')"
        prepend-icon="mdi-account"
        variant="underlined"
        density="compact"
        type="number"
        step="1"
        min="0"
        max="999"
        :rules="[checkPlayerId]"
      />

      <v-select
        v-model="newTeamId"
        :items="teamOptions"
        item-title="label"
        item-value="id"
        :label="$t('modal.bounding_box.edit.new_team_id')"
        prepend-icon="mdi-account-group"
        variant="underlined"
        density="compact"
        :rules="[checkTeamId]"
      />

      <div class="d-flex mt-3" style="gap: 8px">
        <v-btn
          size="small"
          color="primary"
          variant="flat"
          :loading="bboxesStore.isLoading"
          :disabled="!canSubmit"
          @click="applyUpdate"
        >
          {{ $t("button.update") }}
        </v-btn>
        <v-btn
          size="small"
          color="error"
          variant="outlined"
          :loading="bboxesStore.isLoading"
          @click="applyDelete"
        >
          {{ $t("button.delete") }}
        </v-btn>
      </div>

      <v-divider class="my-4" />

      <div class="panel-subheading">{{ $t("annotation_tool.identity.geometry") }}</div>
      <div class="geometry-readout text-medium-emphasis">
        <div>x: {{ box[5].toFixed(4) }} &nbsp; y: {{ box[6].toFixed(4) }}</div>
        <div>w: {{ box[7].toFixed(4) }} &nbsp; h: {{ box[8].toFixed(4) }}</div>
      </div>
      <v-btn
        size="small"
        color="error"
        variant="text"
        class="mt-2"
        prepend-icon="mdi-vector-square-remove"
        @click="removeFromDraft"
      >
        {{ $t("annotation_tool.identity.remove_from_draft") }}
      </v-btn>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useAnnotationToolStore } from "@/stores/annotation_tool";
import { useBboxesStore } from "@/stores/bboxes";
import { useTopViewStore, BBOX_SOURCE_RUN_IDX } from "@/stores/top_view";
import { useVisualizationStore } from "@/stores/visualization";
import { toRgb } from "@/plugins/helpers";

// The identity half of bbox correction, ported out of ModalBboxUpdate.vue. It lives in the
// tool's sidebar rather than in a dialog now: the tool is a full-page workspace, and a modal
// on top of it would cover the very box being corrected.
//
// Geometry is NOT edited here -- that happens directly on the stage (BboxAnnotationTool) and
// stays in the local draft. Identity, by contrast, has a working backend endpoint and is
// written through immediately, so the correction also lands in the analysis view.

const { t } = useI18n();
const store = useAnnotationToolStore();
const bboxesStore = useBboxesStore();
const topViewStore = useTopViewStore();
const visualizationStore = useVisualizationStore();

const box = computed(() => {
  const idx = store.selectedBoxIdx;
  if (idx === null || idx === undefined) return null;
  return store.boxesForFrame(store.currentFrameKey)[idx] ?? null;
});

// bbox_id is derived, never stored: the backend matches on "<frameKey>-<playerId>".
const bboxId = computed(() =>
  box.value ? `${store.currentFrameKey}-${box.value[0]}` : null
);

const currentColor = computed(() =>
  box.value ? toRgb(visualizationStore.getTeamColor(box.value[1]), 0.4) : "#666666"
);

const selectedMode = ref("bbox");
const newPlayerId = ref(null);
const newTeamId = ref(null);

// Reseed the fields whenever a different box is picked, so the panel never shows the previous
// box's pending values.
watch(
  box,
  (value) => {
    if (!value) return;
    newPlayerId.value = value[0];
    newTeamId.value = value[1];
  },
  { immediate: true }
);

// "All frames of this player" disappears once a ReID run is merged: one reid identity can
// cover several original track ids over time, so a global rename by id is ambiguous (see
// bboxesStore.translatePlayerId).
const updateModes = computed(() => [
  { id: "bbox", name: t("modal.bounding_box.edit.modes.bbox") },
  ...(bboxesStore.bboxReidMapping
    ? []
    : [{ id: "allPlayer", name: t("modal.bounding_box.edit.modes.all_player") }]),
  { id: "allTeam", name: t("modal.bounding_box.edit.modes.all_team") },
]);

// Guards against the toggle keeping a mode that just vanished because a ReID merge was applied.
watch(updateModes, (modes) => {
  if (!modes.some((m) => m.id === selectedMode.value)) selectedMode.value = "bbox";
});

const scopeHint = computed(() => {
  if (selectedMode.value === "bbox") return t("modal.bounding_box.edit.modes.info_bbox");
  if (selectedMode.value === "allPlayer")
    return t("modal.bounding_box.edit.modes.info_all_player");
  return t("modal.bounding_box.edit.modes.info_all_team");
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
    { id: -1, label: t("modal.bounding_box.edit.team.unknown") },
    { id: 0, label: t("modal.bounding_box.edit.team.ball") },
    { id: 1, label: t("modal.bounding_box.edit.team.rest") },
    { id: 2, label: t("modal.bounding_box.edit.team.referee") },
    ...existing.map((id) => ({ id, label: t("modal.bounding_box.edit.team.team", { id }) })),
  ];

  if (nextId <= 12) {
    options.push({ id: nextId, label: t("modal.bounding_box.edit.team.new_team", { id: nextId }) });
  }

  return options;
});

const checkPlayerId = (value) => {
  if (value === null || value === undefined || value === "") return t("field.required");
  if (value < 0) return t("modal.bounding_box.edit.rules.player_min");
  if (value > 999) return t("modal.bounding_box.edit.rules.player_max");
  const idsInFrame = store.boxesForFrame(store.currentFrameKey).map((b) => Number(b[0]));
  if (idsInFrame.includes(Number(value)) && Number(value) !== Number(box.value?.[0])) {
    return t("modal.bounding_box.edit.rules.player_duplicate");
  }
  return true;
};

const checkTeamId = (value) => {
  if (value === null || value === undefined || value === "") return t("field.required");
  return true;
};

// Unlike ModalBboxUpdate, which only checked for non-null, the buttons here also wait for the
// rules to actually pass -- submitting a duplicate id silently did nothing useful before.
const canSubmit = computed(() => {
  if (!box.value) return false;
  if (checkTeamId(newTeamId.value) !== true) return false;
  if (selectedMode.value === "allTeam") return true;
  return checkPlayerId(newPlayerId.value) === true;
});

// The payload bboxesStore expects. applyAll* are derived from the active scope rather than
// kept as state -- in ModalBboxUpdate they were set but never reset, so switching scope
// within one open dialog could carry a stale flag into the next request.
const buildPayload = () => ({
  bytetrackRunId: box.value[BBOX_SOURCE_RUN_IDX] ?? bboxesStore.bboxPluginRunId,
  bboxId: bboxId.value,
  playerId: box.value[0],
  teamId: box.value[1],
  newPlayerId: newPlayerId.value,
  newTeamId: newTeamId.value,
  applyAllPlayerId: selectedMode.value === "allPlayer",
  applyAllTeamId: selectedMode.value === "allTeam",
});

// Goes through bboxesStore rather than posting directly: that store carries the three-way
// refresh (ball run / active team-clustering-or-reid merge / plain tracker run) that keeps a
// client-side merge from being dropped by the server's un-merged response.
const applyUpdate = async () => {
  const frameKey = store.currentFrameKey;
  await bboxesStore.updateBboxData(buildPayload());
  // A drafted frame holds its own copy of the boxes, so pull the just-written identity back
  // into it -- otherwise the draft (and with it the export) would keep the stale ids.
  store.syncDraftIdentities(frameKey);
};

const applyDelete = async () => {
  const frameKey = store.currentFrameKey;
  await bboxesStore.deleteBboxData(buildPayload());
  if (store.drafts[frameKey]) {
    store.removeBox(frameKey, store.selectedBoxIdx);
  }
  store.selectedBoxIdx = null;
};

// Local-only removal: drops the box from the correction draft without touching the stored
// plugin output. For "the tracker invented a player that isn't there" without also rewriting
// the run everyone else is looking at.
const removeFromDraft = () => {
  store.removeBox(store.currentFrameKey, store.selectedBoxIdx);
};
</script>

<style scoped>
.identity-panel {
  padding: 12px 14px;
  min-width: 0;
}

.panel-heading {
  font-size: 1rem;
  font-weight: 500;
  margin-bottom: 10px;
}

.panel-subheading {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: rgba(var(--v-theme-on-surface), 0.6);
  margin-bottom: 4px;
}

.panel-empty {
  font-size: 0.85rem;
  padding: 12px 0;
}

.scope-toggle {
  width: 100%;
}

.scope-toggle :deep(.v-btn) {
  flex: 1 1 0;
  font-size: 0.7rem;
  min-width: 0;
}

.geometry-readout {
  font-family: monospace;
  font-size: 0.75rem;
  line-height: 1.6;
}
</style>
