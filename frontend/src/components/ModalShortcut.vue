<template>
  <v-dialog v-model="dialog" max-width="1000">
    <v-card>
      <v-toolbar color="primary" dark class="pl-6 pr-1 text-h6">
        {{ $t("modal.shortcut.title") }}

        <v-spacer />

        <v-btn icon @click="dialog = false" variant="plain" color="grey">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-toolbar>

      <v-card-text>
        <v-text-field
          v-model="search"
          append-inner-icon="mdi-magnify"
          label="Search"
          variant="underlined"
          hide-details
          class="mt-n2 mb-4"
        />

        <v-data-table
          :headers="headers"
          :items="items"
          :items-per-page="10"
          class="elevation-1"
          :search="search"
        >
          <template v-slot:item.name="{ value }">
            <v-chip class="annotation-chip">
              <v-btn disable icon x-small :color="value.color" class="mr-1">
                <v-icon>mdi-palette</v-icon>
              </v-btn>
              {{ value.name }}
            </v-chip>
          </template>

          <template v-slot:item.actions="{ value }">
            <v-text-field
              solo
              flat
              single-line
              hide-details
              @keydown="onKeydown(value, $event)"
              @click:append-outer="clear(value)"
              append-outer-icon="mdi-close"
            >
              <template v-slot:prepend-inner>
                <v-chip v-for="key in value.keys" :key="key">
                  <span>{{ key }}</span>
                </v-chip>
              </template>
            </v-text-field>
          </template>
        </v-data-table>

        <v-row class="mt-6 mb-n2 justify-center">
          <v-btn class="mt-n2" @click="submit" :disabled="isSubmitting">
            {{ $t("modal.shortcut.update") }}
          </v-btn>
        </v-row>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { useAnnotationShortcutStore } from "@/stores/annotation_shortcut";
import { useShortcutStore } from "@/stores/shortcut";
import { useAnnotationStore } from "@/stores/annotation";

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
});

const dialog = ref(props.modelValue);
const isSubmitting = ref(false);
const search = ref("");
const items = ref([]);

const annotationShortcutStore = useAnnotationShortcutStore();
const shortcutStore = useShortcutStore();
const annotationStore = useAnnotationStore();

const headers = ref([
  { title: "Annotation", key: "name" },
  { title: "Shortcut", sortable: false, key: "actions" },
]);

const annotations = computed(() => annotationStore.nonTranscripts);
const annotationShortcuts = computed(() => annotationShortcutStore.all);
const shortcuts = computed(() => shortcutStore.all);

const onKeydown = (item, event) => {
  event.preventDefault();
  let newKeys = [];
  if (event.ctrlKey) newKeys.push("Ctrl");
  if (event.shiftKey) newKeys.push("Shift");
  const lowerChar = event.key.toLowerCase();
  if (lowerChar.length === 1) newKeys.push(lowerChar);
  item.keys = newKeys;
};

const clear = (item) => {
  item.keys = [];
};

const submit = async () => {
  if (isSubmitting.value) return;
  isSubmitting.value = true;
  const shortcutsData = items.value.map((e) => ({ id: e.id, keys: e.keys }));
  await annotationShortcutStore.update({ annotationShortcuts: shortcutsData });
  isSubmitting.value = false;
  dialog.value = false;
};

watch(
  () => dialog.value,
  (value) => {
    if (value) {
      items.value = annotations.value.map((e) => ({ ...e }));
      const lutAnnotationShortcuts = Object.fromEntries(
        annotationShortcuts.value.map((e) => [e.annotation_id, e])
      );
      const lutShortcuts = Object.fromEntries(shortcuts.value.map((e) => [e.id, e]));
      items.value.forEach((e) => {
        if (lutAnnotationShortcuts[e.id]) {
          const annotationShortcut = lutAnnotationShortcuts[e.id];
          e.keys = lutShortcuts[annotationShortcut.shortcut_id]?.keys || [];
        } else {
          e.keys = [];
        }
      });
    }
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

watch(
  () => dialog.value,
  (value) => {
    emit("update:modelValue", value);
  }
);
</script>

<style>
.annotation-chip {
  height: auto !important;
}
.annotation-chip .v-chip__content {
  max-width: 100%;
  height: auto;
  min-height: 32px;
  white-space: pre-wrap;
  padding: 5px 0;
}
</style>
