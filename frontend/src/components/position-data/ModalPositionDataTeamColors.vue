<template>
  <v-dialog v-model="dialog" width="800">
    <v-card>
      <v-toolbar color="primary">
        <v-toolbar-title class="text-h6">
          {{ $t("modal.position_data.team_colors.title") }}
        </v-toolbar-title>

        <template #append>
          <v-btn icon="mdi-close" @click="dialog = false" variant="plain" color="grey" />
        </template>
      </v-toolbar>

      <v-card-text style="overflow-y: auto">
        <v-row>
          <v-col cols="6" v-for="(color, teamId) in teamColors" :key="team" class="py-2 mt-2">
            <v-card class="pa-2">
              <div class="mb-2 d-flex justify-center">
                {{ color }}
              </div>
              <div class="mb-2 d-flex justify-center">
                <v-color-picker v-model="teamColors[teamId]" :modes="['rgb', 'hex']" />
              </div>
            </v-card>
          </v-col>
        </v-row>

        <v-btn class="mt-6" @click="saveTeamColors">
          {{ $t("button.save") }}
        </v-btn>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { useTopViewStore } from "@/stores/top_view";
import { useVisualizationStore } from "@/stores/visualization";

const topViewStore = useTopViewStore();
const visualizationStore = useVisualizationStore();

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

const teamColors = ref({});
Object.values(topViewStore.positionDataTopView).forEach((entries) => {
  entries.forEach((p) => {
    if (p[1] !== 1) teamColors.value[p[1]] = visualizationStore.getTeamColor(p[1]);
  });
});

function saveTeamColors() {
  for (const [teamId, newColor] of Object.entries(teamColors.value)) {
    visualizationStore.setTeamColor(Number(teamId), newColor);
  }
  dialog.value = false;
}
</script>
