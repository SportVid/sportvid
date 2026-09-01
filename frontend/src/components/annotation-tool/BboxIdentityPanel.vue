<template>
  <div class="identity-panel">
    <div class="panel-heading">{{ $t("annotation_tool.identity.title") }}</div>

    <div v-if="!box" class="panel-empty text-medium-emphasis">
      {{ $t("annotation_tool.identity.no_selection") }}
    </div>

    <template v-else>
      <!-- What this box currently is, side by side -- three short readouts rather than three
           chips that wrap in a panel this narrow. -->
      <div class="id-row">
        <div class="id-cell">
          <span class="id-label">{{ $t("annotation_tool.identity.box") }}</span>
          <span class="id-value">{{ bboxId }}</span>
        </div>
        <div class="id-cell">
          <span class="id-label">{{ $t("annotation_tool.identity.player") }}</span>
          <span class="id-value">{{ box[0] }}</span>
        </div>
        <div class="id-cell" :style="{ backgroundColor: currentColor }">
          <span class="id-label">{{ $t("annotation_tool.identity.team") }}</span>
          <span class="id-value">{{ box[1] }}</span>
        </div>
      </div>

      <div class="panel-subheading">{{ $t("annotation_tool.identity.scope") }}</div>
      <!-- Stacked: a three-way toggle laid side by side was unreadable at this width. -->
      <v-radio-group v-model="selectedMode" density="compact" hide-details class="scope-group">
        <v-radio
          v-for="mode in updateModes"
          :key="mode.id"
          :value="mode.id"
          :label="mode.name"
          density="compact"
        />
      </v-radio-group>

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

      <!-- Local, like every other correction here: the change lands in the draft and reaches
           the backend only when the session is submitted (see AnnotationView's
           submitCorrections). Disabled until something actually differs, same as the
           toolbox's delete and discard actions. -->
      <v-btn
        block
        size="small"
        color="primary"
        variant="flat"
        class="mt-4"
        :disabled="!canSubmit"
        @click="applyUpdate"
      >
        {{ $t("button.update") }}
      </v-btn>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useAnnotationToolStore } from "@/stores/annotation_tool";
import { useBboxesStore } from "@/stores/bboxes";
import { useTopViewStore } from "@/stores/top_view";
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

// Unlike ModalBboxUpdate, which only checked for non-null, the button here also waits for the
// rules to actually pass -- submitting a duplicate id silently did nothing useful before --
// and for the fields to actually differ from what the box already says.
const hasChange = computed(() => {
  if (!box.value) return false;
  if (Number(newTeamId.value) !== Number(box.value[1])) return true;
  if (selectedMode.value === "allTeam") return false;
  return Number(newPlayerId.value) !== Number(box.value[0]);
});

const canSubmit = computed(() => {
  if (!box.value || !hasChange.value) return false;
  if (checkTeamId(newTeamId.value) !== true) return false;
  if (selectedMode.value === "allTeam") return true;
  return checkPlayerId(newPlayerId.value) === true;
});

// Local only -- the store keeps the change together with the scope it was made with, and
// AnnotationView's submit replays it against the backend, where "all boxes of this player"
// can mean the whole run rather than just the sampled review frames.
const applyUpdate = () => {
  store.applyIdentity(store.currentFrameKey, store.selectedBoxIdx, {
    newPlayerId: selectedMode.value === "allTeam" ? null : newPlayerId.value,
    newTeamId: newTeamId.value,
    scope: selectedMode.value,
  });
};
</script>

<style scoped>
.identity-panel {
  padding: 12px 14px;
  min-width: 0;
}

.id-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px;
  margin-bottom: 24px;
}

.id-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  min-width: 0;
  padding: 4px 6px;
  border-radius: 6px;
  background-color: rgba(var(--v-theme-on-surface), 0.06);
}

.id-label {
  font-size: 0.62rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  opacity: 0.7;
}

.id-value {
  font-size: 0.82rem;
  font-weight: 600;
  overflow-wrap: anywhere;
}

.scope-group {
  /* Same breathing room below as the id readouts leave above the scope section. */
  margin: -4px 0 24px;
}

.scope-group :deep(.v-label) {
  font-size: 0.8rem;
  opacity: 1;
}

/* Vuetify's radio is sized for a form, not for a 280px side panel. */
.scope-group :deep(.v-selection-control) {
  --v-selection-control-size: 26px;
  min-height: 26px;
}

.scope-group :deep(.v-selection-control__input) {
  width: 26px;
  height: 26px;
}

.scope-group :deep(.v-selection-control__input .v-icon) {
  font-size: 17px;
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

</style>
