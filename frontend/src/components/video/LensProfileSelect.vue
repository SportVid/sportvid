<template>
  <div data-tour="lens-profile-select">
    <div class="text-caption text-grey text-uppercase mb-2">
      {{ $t("lens_profile.heading") }}
    </div>

    <!-- The profile is stored on the video, and which profiles fit it (plus which recording modes
         they have) follows from its resolution -- known once the upload has been converted, see
         the backend's is_compatible/recording_modes. -->
    <v-alert
      v-if="!videoReady"
      type="info"
      density="compact"
      variant="tonal"
      border="start"
      style="font-size: 0.8rem"
    >
      {{ $t("lens_profile.video_not_ready") }}
    </v-alert>

    <template v-else>
      <v-row dense>
        <v-col cols="12" md="6">
          <v-autocomplete
            v-model="brand"
            :items="brandItems"
            :label="$t('lens_profile.brand')"
            density="compact"
            variant="underlined"
            clearable
            hide-details
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-autocomplete
            v-model="model"
            :items="modelItems"
            :label="$t('lens_profile.model')"
            :disabled="!brand"
            density="compact"
            variant="underlined"
            clearable
            hide-details
          />
        </v-col>
      </v-row>

      <!-- The "other aspect ratios" switch sits with this select because it decides what is in it. -->
      <div class="d-flex align-center ga-4 mt-2">
        <v-select
          v-model="profileId"
          :items="profileItems"
          item-title="title"
          item-value="value"
          :label="$t('lens_profile.profile')"
          :disabled="!brand"
          :loading="lensProfileStore.isLoading"
          :no-data-text="noProfilesText"
          density="compact"
          variant="underlined"
          clearable
          hide-details
          class="flex-grow-1"
        >
          <template #item="{ props: itemProps, item }">
            <v-list-item v-bind="itemProps" :subtitle="item.raw.subtitle" />
          </template>
        </v-select>
        <v-checkbox
          v-model="showIncompatible"
          :label="$t('lens_profile.show_incompatible')"
          hide-details
          density="compact"
          class="flex-shrink-0"
        />
      </div>

      <!-- The EIS crop the video was recorded with: a stabilised recording shows a cropped, and
           therefore differently distorted, part of the calibrated frame. -->
      <v-select
        v-if="selectedProfile && recordingModeItems.length > 1"
        v-model="lensCrop"
        :items="recordingModeItems"
        item-title="title"
        item-value="value"
        :label="$t('lens_profile.recording_mode')"
        :hint="$t('lens_profile.recording_mode_hint')"
        persistent-hint
        density="compact"
        variant="underlined"
        class="mt-2"
      >
        <template #item="{ props: itemProps, item }">
          <v-list-item v-bind="itemProps" :subtitle="item.raw.subtitle" />
        </template>
      </v-select>

      <v-alert
        v-if="selectedProfile && selectedProfile.eis === 'unknown'"
        type="warning"
        density="compact"
        variant="tonal"
        border="start"
        class="mt-3"
        style="font-size: 0.8rem"
      >
        {{ $t("lens_profile.eis_unknown_warning") }}
      </v-alert>

      <v-alert
        v-if="selectedProfile && selectedProfile.aspect_fit && selectedProfile.aspect_fit !== 'same'"
        type="warning"
        density="compact"
        variant="tonal"
        border="start"
        class="mt-3"
        style="font-size: 0.8rem"
      >
        {{ $t(`lens_profile.aspect_${selectedProfile.aspect_fit}`) }}
      </v-alert>

      <div class="text-caption text-grey mt-2">{{ $t("lens_profile.none_hint") }}</div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { useI18n } from "vue-i18n";
import { useLensProfileStore } from "@/stores/lens_profile";

const { t } = useI18n();
const lensProfileStore = useLensProfileStore();

const props = defineProps({
  // the video entry (id, width, height) the profile is picked for
  video: {
    type: Object,
    default: null,
  },
  // { lensProfileId, lensCrop } -- the picked profile. Nothing is written here: whoever embeds
  // this persists the selection when its own action runs (starting the calibration, saving the
  // video's settings), see applyLensProfileSelection in usePluginParams.js.
  modelValue: {
    type: Object,
    default: () => ({ lensProfileId: null, lensCrop: 1.0 }),
  },
});

const emit = defineEmits(["update:modelValue"]);

const videoId = computed(() => props.video?.id ?? null);
const videoReady = computed(() => !!(props.video?.width && props.video?.height));

const brand = ref(null);
const model = ref(null);
const showIncompatible = ref(false);

const profileId = computed({
  get: () => props.modelValue?.lensProfileId ?? null,
  set: (value) => emit("update:modelValue", { lensProfileId: value, lensCrop: lensCrop.value }),
});
const lensCrop = computed({
  get: () => props.modelValue?.lensCrop ?? 1.0,
  set: (value) => emit("update:modelValue", { lensProfileId: profileId.value, lensCrop: value }),
});

const brandItems = computed(() => {
  // The endpoint returns one row per (brand, group), and a brand can be filed under several
  // groups (the repository's top-level camera families) -- the picker filters by brand alone, so
  // those rows collapse into one entry that names all of its groups.
  const byBrand = new Map();
  for (const entry of lensProfileStore.brands) {
    const groups = byBrand.get(entry.brand) ?? [];
    groups.push(entry.group);
    byBrand.set(entry.brand, groups);
  }
  return [...byBrand].map(([brandName, groups]) => ({
    title: `${brandName} (${groups.join(", ")})`,
    value: brandName,
  }));
});
const modelItems = computed(() =>
  lensProfileStore.models.map((entry) => ({ title: entry.model, value: entry.model }))
);

const profileItems = computed(() =>
  lensProfileStore.profiles.map((entry) => ({
    title: entry.name,
    subtitle: [
      `${entry.calib_width}x${entry.calib_height}`,
      t(`lens_profile.eis_${entry.eis}`),
      entry.rms_error != null ? t("lens_profile.rms", { value: entry.rms_error.toFixed(2) }) : null,
      entry.official ? t("lens_profile.official") : null,
      entry.compatible === false ? t("lens_profile.incompatible") : null,
    ]
      .filter(Boolean)
      .join(" · "),
    value: entry.id,
  }))
);

const selectedProfile = computed(
  () => lensProfileStore.profiles.find((entry) => entry.id === profileId.value) ?? null
);

const modeLabel = (mode) =>
  `${mode.label} (crop ${mode.crop})${mode.listed ? "" : ` -- ${t("lens_profile.mode_unlisted")}`}`;

const recordingModeItems = computed(() =>
  (selectedProfile.value?.recording_modes ?? []).map((mode) => ({
    title: modeLabel(mode),
    subtitle: (mode.sizes ?? []).join(", "),
    value: mode.crop,
  }))
);

const noProfilesText = computed(() =>
  showIncompatible.value ? t("lens_profile.no_profiles") : t("lens_profile.no_profiles_compatible")
);

const loadProfiles = () =>
  lensProfileStore.fetchProfiles({
    brand: brand.value,
    model: model.value,
    videoId: videoId.value,
    compatibleOnly: !showIncompatible.value,
  });

watch(brand, async (value, previous) => {
  // Only a brand the user switched away from clears the model. On open the assigned profile's
  // brand and model are filled in together (see onMounted), and this watcher must not wipe the
  // model it was just given -- that is what used to leave the camera model empty every time the
  // dialog was reopened.
  if (previous) model.value = null;
  await lensProfileStore.fetchModels({ brand: value });
  loadProfiles();
});
watch([model, showIncompatible], loadProfiles);

// A profile's recording modes come sorted with the plausible ones first (the video's own aspect
// ratio, largest crop), so the first is the default; a crop that is still offered for the newly
// picked profile is kept.
watch(selectedProfile, (profile) => {
  if (!profile) return;
  const modes = profile.recording_modes ?? [];
  if (!modes.some((mode) => mode.crop === lensCrop.value)) {
    lensCrop.value = modes.length > 0 ? modes[0].crop : 1.0;
  }
});

onMounted(async () => {
  lensProfileStore.fetchBrands();
  // Start out on the assigned profile's camera, so its own select shows it and switching to a
  // neighbouring profile or another recording mode needs no searching.
  if (profileId.value) {
    const assigned =
      lensProfileStore.byId[profileId.value] ??
      (await lensProfileStore.fetchProfile({ id: profileId.value, videoId: videoId.value }));
    if (assigned) {
      brand.value = assigned.brand;
      model.value = assigned.model;
    }
  }
});
</script>
