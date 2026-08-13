<template>
  <v-dialog v-model="dialog" width="500">
    <v-card>
      <v-toolbar color="primary">
        <v-toolbar-title class="text-h6">
          {{ $t("modal.event_data.select.title") }}
        </v-toolbar-title>

        <template #append>
          <v-btn icon="mdi-close" @click="dialog = false" variant="plain" color="grey" />
        </template>
      </v-toolbar>

      <v-card-text style="max-height: 500px; overflow-y: auto">
        <!-- Only ever a flat list of manual uploads for now -- no CV-run tab like
             ModalPositionDataSelect's, since there's no plugin to pick a run from yet
             (see EventDataMenu.vue's disabled "Detect events" button). -->
        <v-list v-if="eventsStore.eventDataSets.length" density="compact" class="mt-2">
          <v-list-item
            v-for="data in eventsStore.eventDataSets"
            :key="data.id"
            class="mr-4"
            :active="selectedId === data.id"
            @click="selectedId = data.id"
          >
            <template #append>
              <v-btn
                v-if="canWrite"
                size="x-small"
                color="red"
                variant="plain"
                class="mr-1"
                @click.stop="eventsStore.deleteEventDataSet(data.id)"
              >
                <v-icon>mdi-delete</v-icon>
              </v-btn>
            </template>
            <v-list-item-title>{{ data.title }}</v-list-item-title>
            <v-list-item-subtitle>{{ formatLocalDate(data.createdAt) }}</v-list-item-subtitle>
          </v-list-item>
        </v-list>

        <div v-else class="text-center my-4">
          <div class="text-grey mb-3">{{ $t("modal.event_data.select.empty") }}</div>
          <!-- Backdoor while there's no real detector and no reason to make anyone fill out
               the upload form just to see mocked events -- generates+selects a reusable demo
               entry in one click (see eventsStore.loadDemoEventData). -->
          <v-btn @click="loadDemo">{{ $t("modal.event_data.select.demo") }}</v-btn>
        </div>

        <v-btn
          v-if="eventsStore.eventDataSets.length"
          class="mt-4 mb-n2"
          :disabled="!selectedId"
          @click="confirmSelection"
        >
          {{ $t("button.select") }}
        </v-btn>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { useEventsStore } from "@/stores/events";
import { usePlayerStore } from "@/stores/player";
import { useUserStore } from "@/stores/user";

const eventsStore = useEventsStore();
const playerStore = usePlayerStore();
const userStore = useUserStore();

const canWrite = computed(() => {
  if (userStore.role === "admin") return true;
  const ownerUsername = playerStore.video?.owner_username;
  if (!ownerUsername) return true;
  return ownerUsername === userStore.username;
});

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

// Pre-select whatever's already active (if any) so reopening this to switch data sets doesn't
// default back to nothing picked.
const selectedId = ref(eventsStore.selectedEventDataSetId);

const formatLocalDate = (dateString) => {
  if (!dateString) return "";
  const date = new Date(dateString);
  const isoDate = date.toISOString().slice(0, 10);
  const localTime = date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  return `${isoDate} ${localTime}`;
};

const confirmSelection = () => {
  if (!selectedId.value) return;
  eventsStore.selectEventDataSet(selectedId.value);
  dialog.value = false;
};

const loadDemo = () => {
  eventsStore.loadDemoEventData();
  dialog.value = false;
};
</script>
