<template>
  <v-dialog v-model="dialog" width="700px">
    <v-card>
      <v-toolbar color="primary">
        <v-toolbar-title class="text-h6">
          {{ $t("modal.position_data.rename.title") }}
        </v-toolbar-title>
        <template #append>
          <v-btn icon="mdi-close" @click="dialog = false" variant="plain" color="grey" />
        </template>
      </v-toolbar>

      <v-card-text class="d-flex align-center">
        <v-text-field
          v-model="name"
          :label="$t('modal.position_data.rename.name')"
          prepend-icon="mdi-pencil"
          variant="underlined"
          class="mr-6"
        />

        <v-btn @click="renamePositionData(props.positionDataId, name)" :disabled="!name">
          {{ $t("button.update") }}
        </v-btn>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { usePositionDataStore } from "@/stores/position_data";

const positionDataStore = usePositionDataStore();

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  positionDataId: {
    type: Number,
    required: true,
  },
});

const emit = defineEmits(["update:modelValue"]);

const nameProxy = ref(null);
const name = computed({
  get() {
    const name = positionDataStore.positionDataList.find(
      (data) => data.id === props.positionDataId
    )?.name;
    return nameProxy.value === null ? name : nameProxy.value;
  },
  set(val) {
    nameProxy.value = val;
  },
});

const renamePositionData = (positionDataId, name) => {
  positionDataStore.renamePositionData(positionDataId, name);
  dialog.value = false;
};

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
</script>
