<template>
  <v-dialog v-model="dialog" width="400px">
    <v-card>
      <v-toolbar color="primary" dark class="pl-6 pr-1 text-h6">
        {{ $t("modal.position_data.select") }}

        <v-spacer></v-spacer>

        <v-btn icon @click="dialog = false" variant="plain" color="grey">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-toolbar>

      <v-card-text>
        <v-list density="compact" style="height: 210px; overflow-y: auto">
          <v-list-item
            v-for="plugin in bytetrackRuns"
            :key="plugin.type"
            class="mr-4"
            @click="loadBytetrackData(plugin.id)"
          >
            {{ plugin.type }} ({{ plugin.date }})
          </v-list-item>
        </v-list>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { usePlayerStore } from "@/stores/player";
import { useBboxesStore } from "@/stores/bboxes";
import { usePluginRunStore } from "@/stores/plugin_run";

const playerStore = usePlayerStore();
const bboxesStore = useBboxesStore();
const pluginRunStore = usePluginRunStore();

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
});
const emit = defineEmits();

const dialog = ref(props.modelValue);

const bytetrackRuns = computed(() => {
  return pluginRunStore
    .forVideo(playerStore.videoId)
    .filter((e) => e.type === "bytetrack" && e.status === "DONE")
    .map((pluginRun, index) => ({
      id: index,
      type: "Bytetrack",
      date: pluginRun.date
        .replace("T", " ")
        .replace("Z", "")
        .substring(0, pluginRun.date.length - 8),
    }));
});

const loadBytetrackData = (index) => {
  bboxesStore.bboxPluginRun = index;
  dialog.value = false;
};

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
