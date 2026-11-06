<template>
  <v-dialog v-model="dialog" width="700">
    <v-card>
      <v-toolbar color="primary">
        <v-toolbar-title class="text-h6">{{ $t("lens_profile.title") }}</v-toolbar-title>

        <template #append>
          <v-btn icon="mdi-close" @click="dialog = false" variant="plain" color="grey" />
        </template>
      </v-toolbar>

      <v-card-text class="pt-4">
        <LensProfileSelect v-model="selection" :video="videoData" />

        <v-alert
          v-if="error"
          type="error"
          density="compact"
          variant="tonal"
          border="start"
          class="mt-3"
          style="font-size: 0.8rem"
        >
          {{ error }}
        </v-alert>

        <v-row class="mt-4">
          <v-spacer />
          <v-btn :loading="saving" :disabled="!selection" @click="submit">{{
            $t("button.save")
          }}</v-btn>
        </v-row>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed } from "vue";
import { useI18n } from "vue-i18n";
import { usePlayerStore } from "@/stores/player";
import { useVideoStore } from "@/stores/video";
import { useLensProfileStore } from "@/stores/lens_profile";
import LensProfileSelect from "@/components/video/LensProfileSelect.vue";

const { t } = useI18n();
const playerStore = usePlayerStore();
const videoStore = useVideoStore();
const lensProfileStore = useLensProfileStore();

const props = defineProps({
  video: {
    type: [String, Number],
    required: true,
  },
  modelValue: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["update:modelValue"]);

const dialog = computed({
  get: () => props.modelValue,
  set: (value) => emit("update:modelValue", value),
});

const videoData = computed(() => videoStore.get(props.video) ?? null);

const saving = ref(false);
const error = ref(null);
// What the picker reports: it starts out on what the video carries and reports every change
// afterwards (see LensProfileSelect). Nothing here re-syncs it from the video entry -- that entry
// is replaced on every refresh of the gallery (the live event stream and its polling fallback
// both do that while a plugin run is going), which used to throw the user's pick away again and
// made saving appear to do nothing. Null only until the picker has mounted.
const selection = ref(null);

const submit = async () => {
  if (saving.value || !selection.value) return;
  saving.value = true;
  error.value = null;
  try {
    const res = await lensProfileStore.setForVideo({
      videoId: props.video,
      lensProfileId: selection.value.lensProfileId,
      lensCrop: selection.value.lensCrop,
    });
    if (res.status !== "ok") {
      const key = `lens_profile.error_${res.type ?? "generic"}`;
      error.value = t(key) === key ? (res.reason ?? t("lens_profile.error_generic")) : t(key);
      return;
    }
    // the response is the updated video entry -- patch it into the gallery's map so it and a
    // later reopen show the assignment without refetching the whole list, and into the player's
    // single open video if it happens to be this one (the calibration rule reads it from there)
    videoStore.upsert(res.entry);
    if (playerStore.video?.id === res.entry.id) {
      await playerStore.fetchVideo({ videoId: res.entry.id });
    }
    dialog.value = false;
  } finally {
    saving.value = false;
  }
};
</script>
