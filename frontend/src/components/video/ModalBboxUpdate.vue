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
                    {{ $t("modal.bounding_box.edit.current_player_id") }}: {{ bbox[0] }}
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
                        {{ currentPlayerId }}
                      </v-chip>
                    </template>

                    <div class="player-team-selector mt-2 pa-1">
                      <div
                        v-for="playerId in playerOptions"
                        :key="playerId"
                        class="player-dot"
                        :style="{
                          backgroundColor: toRgb(playerColors[playerId], 0.7),
                          color: '#222',
                          borderColor: toRgb(playerColors[playerId], 0.7),
                        }"
                        @click="currentPlayerId = playerId"
                      >
                        {{ playerId }}
                      </div>
                    </div>
                  </v-menu>

                  <v-chip v-if="mode.id === 'bbox' || mode.id === 'allPlayer'" color="#666666">
                    {{ $t("modal.bounding_box.edit.current_team_id") }}: {{ bbox[1] }}
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
                        {{ currentTeamId }}
                      </v-chip>
                    </template>
                    <div class="player-team-selector mt-2 pa-1">
                      <div
                        v-for="teamId in teamOptions"
                        :key="teamId"
                        class="team-dot"
                        :style="{
                          backgroundColor: toRgb(teamId, 0.7),
                          color: '#222',
                        }"
                        @click="currentTeamId = teamId"
                      >
                        {{ teamId }}
                      </div>
                    </div>
                  </v-menu>
                </div>

                <template v-if="mode.id === 'bbox'">
                  <v-text-field
                    v-model="newPlayerId"
                    :label="$t('modal.bounding_box.edit.new_player_id')"
                    prepend-icon="mdi-account"
                    variant="underlined"
                    type="number"
                    step="1"
                    min="1"
                    max="999"
                    :rules="[checkNumber]"
                  />

                  <v-row>
                    <v-col cols="5">
                      <v-text-field
                        v-model="newTeamId"
                        :label="$t('modal.bounding_box.edit.new_team_id')"
                        prepend-icon="mdi-account-group"
                        variant="underlined"
                        class="mt-3"
                      />
                    </v-col>

                    <v-col cols="7" class="d-flex align-center">
                      <v-expansion-panels>
                        <v-expansion-panel variant="underlined" class="mb-1">
                          <v-expansion-panel-title>
                            {{ $t("modal.bounding_box.edit.new_team_id_picker") }}
                          </v-expansion-panel-title>
                          <v-expansion-panel-text>
                            <v-color-picker
                              v-model="newTeamId"
                              mode="hex"
                              hide-inputs
                              width="250px"
                            />
                          </v-expansion-panel-text>
                        </v-expansion-panel>
                      </v-expansion-panels>
                    </v-col>
                  </v-row>
                </template>

                <template v-if="mode.id === 'allPlayer'">
                  <v-text-field
                    v-model="newPlayerId"
                    :label="$t('modal.bounding_box.edit.new_player_id')"
                    prepend-icon="mdi-account"
                    variant="underlined"
                    type="number"
                    step="1"
                    min="1"
                    max="999"
                    :rules="[checkNumber]"
                  />

                  <v-row>
                    <v-col cols="5">
                      <v-text-field
                        v-model="newTeamId"
                        :label="$t('modal.bounding_box.edit.new_team_id')"
                        prepend-icon="mdi-account-group"
                        variant="underlined"
                        class="mt-3"
                      />
                    </v-col>

                    <v-col cols="7" class="d-flex align-center">
                      <v-expansion-panels>
                        <v-expansion-panel variant="underlined" class="mb-1">
                          <v-expansion-panel-title>
                            {{ $t("modal.bounding_box.edit.new_team_id_picker") }}
                          </v-expansion-panel-title>
                          <v-expansion-panel-text>
                            <v-color-picker
                              v-model="newTeamId"
                              mode="hex"
                              hide-inputs
                              width="250px"
                            />
                          </v-expansion-panel-text>
                        </v-expansion-panel>
                      </v-expansion-panels>
                    </v-col>
                  </v-row>
                </template>

                <template v-if="mode.id === 'allTeam'">
                  <v-row>
                    <v-col cols="5">
                      <v-text-field
                        v-model="newTeamId"
                        :label="$t('modal.bounding_box.edit.new_team_id')"
                        prepend-icon="mdi-account-group"
                        variant="underlined"
                        class="mt-3"
                      />
                    </v-col>

                    <v-col cols="7" class="d-flex align-center">
                      <v-expansion-panels>
                        <v-expansion-panel variant="underlined" class="mb-1">
                          <v-expansion-panel-title>
                            {{ $t("modal.bounding_box.edit.new_team_id_picker") }}
                          </v-expansion-panel-title>
                          <v-expansion-panel-text>
                            <v-color-picker
                              v-model="newTeamId"
                              mode="hex"
                              hide-inputs
                              width="250px"
                            />
                          </v-expansion-panel-text>
                        </v-expansion-panel>
                      </v-expansion-panels>
                    </v-col>
                  </v-row>
                </template>
              </v-tabs-window-item>
            </v-tabs-window>
          </v-col>
        </v-row>

        <v-btn @click="update" :disabled="!newPlayerId || !newTeamId" class="mt-4">
          {{ $t("button.update") }}
        </v-btn>

        <v-btn @click="delete" :disabled="!newPlayerId || !newTeamId" class="mt-4 ml-4">
          {{ $t("button.delete") }}
        </v-btn>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useTopViewStore } from "@/stores/top_view";
import { toRgb } from "@/plugins/helpers";

const topViewStore = useTopViewStore();

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

const currentPlayerId = ref(props.bbox?.[0] || "");
const newPlayerId = ref("");
const currentTeamId = ref(props.bbox?.[1] || "");
const newTeamId = ref("");
const updateSamePlayerId = ref(false);
const updateSameTeamId = ref(false);
watch(
  () => [props.bbox, dialog.value],
  ([bbox, open]) => {
    if (open && bbox) {
      newPlayerId.value = bbox[0];
      newTeamId.value = bbox[1];
    }
  },
  { immediate: true }
);
async function update() {
  emit("update", {
    player_id: newPlayerId.value,
    team_id: newTeamId.value,
    updateSamePlayerId: updateSamePlayerId.value,
    updateSameTeamId: updateSameTeamId.value,
  });
  dialog.value = false;
}

const selectedMode = ref("bytetrack");
const BboxUpdateModes = ref([
  { id: "bbox", name: t("modal.bounding_box.edit.modes.bbox") },
  { id: "allPlayer", name: t("modal.bounding_box.edit.modes.all_player") },
  { id: "allTeam", name: t("modal.bounding_box.edit.modes.all_team") },
]);

const playerOptions = computed(() => {
  const all = Object.values(topViewStore.positionDataTopView).flat();
  return [...new Set(all.map((p) => p[0]))].sort((a, b) => a - b);
});
const teamOptions = computed(() => {
  const all = Object.values(topViewStore.positionDataTopView).flat();
  return [...new Set(all.map((p) => p[1]))].sort((a, b) => a - b);
});
const playerColors = computed(() => {
  const all = Object.values(topViewStore.positionDataTopView).flat();
  const map = {};
  all.forEach((p) => {
    map[p[0]] = p[1];
  });
  return map;
});
const teamColors = computed(() => {
  const all = Object.values(topViewStore.positionDataTopView).flat();
  const map = {};
  all.forEach((p) => {
    map[p[1]] = p[1];
  });
  return map;
});

const checkNumber = (value) => {
  if (!value) {
    return t("field.required");
  }
  if (value < 1) {
    return t("modal.bounding_box.edit.rules.min");
  }
  if (value > 999) {
    return t("modal.bounding_box.edit.rules.max");
  }
  return true;
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

.player-dot {
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
.player-dot:hover {
  transform: scale(1.1);
}

.team-dot {
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  padding: 4px;
}
.team-dot:hover {
  transform: scale(1.1);
}
</style>
