<template>
  <v-dialog v-model="dialog" width="800">
    <v-card>
      <v-toolbar color="primary">
        <v-toolbar-title class="text-h6">
          {{ $t("modal.position_data.entity_colors.title") }}
        </v-toolbar-title>

        <template #append>
          <v-btn icon="mdi-close" @click="dialog = false" variant="plain" color="grey" />
        </template>
      </v-toolbar>

      <v-card-text style="overflow-y: auto">
        <v-row>
          <v-col cols="6" v-for="(color, teamId) in activeTeamColors" :key="teamId" class="py-2">
            <v-card class="pa-2">
              <div class="mb-2 d-flex justify-center">
                {{ getTeamName(teamId) }}
              </div>
              <div class="mb-2 d-flex justify-center">
                <v-color-picker v-model="teamColors[teamId]" :modes="['hex', 'rgb']" />
              </div>
            </v-card>
          </v-col>
        </v-row>

        <!-- Special entities: ball, referee, rest — collapsible -->
        <v-expansion-panels class="mt-4">
          <v-expansion-panel>
            <v-expansion-panel-title>
              {{ $t("modal.position_data.entity_colors.other_entities") }}
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <v-row class="mt-1">
                <v-col cols="6" v-for="id in specialEntityIds" :key="id" class="py-2">
                  <v-card class="pa-2">
                    <div class="mb-2 d-flex justify-center">
                      {{ $t(`modal.position_data.entity_colors.entity_${id}`) }}
                    </div>
                    <div class="mb-2 d-flex justify-center">
                      <v-color-picker v-model="teamColors[id]" :modes="['hex', 'rgb']" />
                    </div>
                  </v-card>
                </v-col>
              </v-row>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>

        <v-btn class="mt-6" @click="saveTeamColors">
          {{ $t("button.save") }}
        </v-btn>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { useTopViewStore } from "@/stores/top_view";
import { useVisualizationStore } from "@/stores/visualization";

const topViewStore = useTopViewStore();
const visualizationStore = useVisualizationStore();

function getTeamName(teamId) {
  const meta = topViewStore.metaDataTopView;
  return meta?.team_ids?.[teamId]?.name;
}

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
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

// Special entity ids: 0=rest, 1=ball, 2=referee
const specialEntityIds = [0, 1, 2];

const teamColors = ref({});
// Initialize special entities
for (const id of specialEntityIds) {
  teamColors.value[id] = visualizationStore.getTeamColor(id);
}
// Initialize active teams
for (const p of topViewStore.precomputedPlayerList) {
  teamColors.value[p.teamId] = visualizationStore.getTeamColor(p.teamId);
}

// Only team_id >= 3 entries for the "teams" section
const activeTeamColors = computed(() => {
  return Object.fromEntries(Object.entries(teamColors.value).filter(([id]) => Number(id) >= 3));
});

function saveTeamColors() {
  for (const [teamId, newColor] of Object.entries(teamColors.value)) {
    visualizationStore.setTeamColor(Number(teamId), newColor);
  }
  dialog.value = false;
}
</script>
