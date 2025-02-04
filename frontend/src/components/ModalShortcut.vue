<template>
  <v-dialog v-model="dialog" max-width="1000" @keydown.esc="dialog = false">
    <v-card>
      <v-card-title class="mb-2">
        {{ $t("modal.shortcut.title") }}
        <v-spacer></v-spacer>
        <v-text-field
          v-model="search"
          append-icon="mdi-magnify"
          label="Search"
          single-line
          hide-details
          class="mt-0 pt-0"
        ></v-text-field>
        <v-btn icon @click="dialog = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>
      <v-card-text>
        <v-data-table
          :headers="headers"
          :items="items"
          :items-per-page="10"
          class="elevation-1"
          :search="search"
        >
          <template v-slot:item_name="{ item }">
            <v-chip class="annotation-chip">
              <v-btn disable icon x-small :color="item.color" class="mr-1">
                <v-icon>mdi-palette</v-icon>
              </v-btn>
              {{ item.name }}
            </v-chip>
          </template>
          <template v-slot:item_actions="{ item }">
            <v-text-field
              solo
              flat
              single-line
              hide-details
              @keydown="onKeydown(item, $event)"
              @click:append-outer="clear(item)"
              append-outer-icon="mdi-close"
            >
              <template v-slot:prepend-inner>
                <v-chip v-for="key in item.keys" :key="key">
                  <span>{{ key }}</span>
                </v-chip>
              </template>
            </v-text-field>
          </template>
        </v-data-table>
      </v-card-text>
      <v-card-actions class="pt-0">
        <v-btn class="mr-4" @click="submit" :disabled="isSubmitting">
          {{ $t("modal.shortcut.update") }}
        </v-btn>
        <v-btn @click="dialog = false">{{ $t("modal.shortcut.close") }}</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import { reactive, ref, computed, watch } from "vue";
import { useAnnotationShortcutStore } from "@/stores/annotation_shortcut";
import { useShortcutStore } from "@/stores/shortcut";
import { useAnnotationStore } from "@/stores/annotation";

export default {
  props: ["value"],
  setup(props, { emit }) {
    const dialog = ref(false);
    const isSubmitting = ref(false);
    const search = ref("");
    const items = ref([]);

    const annotationShortcutStore = useAnnotationShortcutStore();
    const shortcutStore = useShortcutStore();
    const annotationStore = useAnnotationStore();

    const headers = reactive([
      { text: "Annotation", value: "name" },
      { text: "Shortcut", sortable: false, value: "actions" },
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
      const shortcutsData = items.value.map(e => ({ id: e.id, keys: e.keys }));
      await annotationShortcutStore.update({ annotationShortcuts: shortcutsData });
      isSubmitting.value = false;
      dialog.value = false;
    };

    watch(
      () => dialog.value,
      (value) => {
        if (value) {
          items.value = annotations.value.map(e => ({ ...e }));
          const lutAnnotationShortcuts = Object.fromEntries(
            annotationShortcuts.value.map(e => [e.annotation_id, e])
          );
          const lutShortcuts = Object.fromEntries(
            shortcuts.value.map(e => [e.id, e])
          );
          items.value.forEach(e => {
            if (lutAnnotationShortcuts[e.id]) {
              const annotationShortcut = lutAnnotationShortcuts[e.id];
              e.keys = lutShortcuts[annotationShortcut.shortcut_id]?.keys || [];
            } else {
              e.keys = [];
            }
          });
        }
        emit("input", value);
      }
    );

    watch(
      () => props.value,
      (value) => {
        if (value) dialog.value = true;
      }
    );

    return {
      dialog,
      isSubmitting,
      search,
      items,
      headers,
      onKeydown,
      clear,
      submit,
    };
  },
};
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
