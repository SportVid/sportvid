<template>
  <v-dialog v-model="dialog" width="600px">
    <v-card>
      <v-toolbar color="primary" dark class="pl-6 pr-1 text-h6">
        {{ $t("modal.annotation.select_annotation") }}

        <v-spacer></v-spacer>

        <v-btn icon @click="dialog = false" variant="plain" color="grey">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-toolbar>

      <v-card-text>
        <v-list density="compact" style="height: 210px; overflow-y: auto">
          <v-list-item
            v-for="(_, key) in markerStore.annotations"
            :key="key"
            @click="loadAnnotation(key)"
            class="mr-4"
          >
            <template v-slot:prepend>
              <v-btn
                size="x-small"
                color="red"
                variant="plain"
                class="mr-2"
                @click="markerStore.deleteAnnotation(key)"
              >
                <v-icon>mdi-delete</v-icon>
              </v-btn>
            </template>
            {{ key }}
          </v-list-item>
        </v-list>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, onMounted, watch } from "vue";
import { useMarkerStore } from "@/stores/marker";

const markerStore = useMarkerStore();

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
});
const emit = defineEmits();

const dialog = ref(props.modelValue);

const loadAnnotation = (name) => {
  markerStore.loadAnnotation(name);
  dialog.value = false;
};

onMounted(() => {
  markerStore.loadFromLocalStorage();
});

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

<style></style>
