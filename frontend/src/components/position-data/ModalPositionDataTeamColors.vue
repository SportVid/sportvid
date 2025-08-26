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

      <v-card-text>
        <v-row>
          <v-col cols="6" v-for="team in uniqueTeamColors" :key="team" class="py-2 mt-2">
            <v-card class="pa-2">
              <div class="mb-2 d-flex justify-center">
                {{ team === "" ? $t("modal.position_data.team_colors.unlabeled") : team }}
              </div>
              <div class="mb-2 d-flex justify-center">
                <v-color-picker v-model="updatedTeamColors[team]" :modes="['rgba', 'hexa']" />
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
import { color, formatHex } from "d3";

const topViewStore = useTopViewStore();

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

const uniqueTeamColors = computed(() => {
  const set = new Set();
  Object.values(topViewStore.positionDataTopView).forEach((entries) => {
    entries.forEach((p) => set.add(p[1]));
  });
  return Array.from(set);
});
const updatedTeamColors = ref({});
onMounted(() => {
  uniqueTeamColors.value.forEach((team) => {
    updatedTeamColors.value[team] = team === "" ? "#888888" : color(team).formatHex();
  });
});

function saveTeamColors() {
  const mapping = updatedTeamColors.value;

  const updatedPositionData = {};

  for (const [time, entries] of Object.entries(topViewStore.positionDataTopView)) {
    updatedPositionData[time] = entries.map((p) => {
      p[1] = mapping[p[1]];
      return p;
    });
  }

  topViewStore.positionDataTopView = updatedPositionData;
  dialog.value = false;
}
</script>
