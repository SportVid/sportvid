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
            :model-value="brand"
            :items="brandItems"
            :label="$t('lens_profile.brand')"
            density="compact"
            variant="underlined"
            clearable
            hide-details
            @update:model-value="selectBrand"
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-autocomplete
            :model-value="model"
            :items="modelItems"
            :label="$t('lens_profile.model')"
            :disabled="!brand"
            density="compact"
            variant="underlined"
            clearable
            hide-details
            @update:model-value="selectModel"
          />
        </v-col>
      </v-row>

      <!-- The "other aspect ratios" switch sits with this select because it decides what is in it. -->
      <div class="d-flex align-center ga-4 mt-2">
        <v-select
          :model-value="selection.lensProfileId"
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
          @update:model-value="selectProfile"
        >
          <template #item="{ props: itemProps, item }">
            <v-list-item v-bind="itemProps" :subtitle="item.raw.subtitle" />
          </template>
        </v-select>
        <v-checkbox
          :model-value="showIncompatible"
          :label="$t('lens_profile.show_incompatible')"
          hide-details
          density="compact"
          class="flex-shrink-0"
          @update:model-value="toggleIncompatible"
        />
      </div>

      <!-- The EIS crop the video was recorded with: a stabilised recording shows a cropped, and
           therefore differently distorted, part of the calibrated frame. -->
      <v-select
        v-if="selectedProfile && recordingModeItems.length > 1"
        :model-value="selection.lensCrop"
        :items="recordingModeItems"
        item-title="title"
        item-value="value"
        :label="$t('lens_profile.recording_mode')"
        :hint="$t('lens_profile.recording_mode_hint')"
        persistent-hint
        density="compact"
        variant="underlined"
        class="mt-2"
        @update:model-value="selectCrop"
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
import { ref, computed, onMounted } from "vue";
import { useI18n } from "vue-i18n";
import { useLensProfileStore } from "@/stores/lens_profile";

const { t } = useI18n();
const lensProfileStore = useLensProfileStore();

const props = defineProps({
  // The video entry the profile is picked for. It is also where the picker takes its starting
  // point from (its "lens_profile_id"/"lens_crop"): the assignment lives on the video, so there
  // is exactly one place this component reads it from, once, when it mounts.
  video: {
    type: Object,
    default: null,
  },
  // Write-only: v-model target the picked { lensProfileId, lensCrop } is reported through.
  // Deliberately never read back -- the selection below is this component's own state, so a host
  // that replaces its copy (or a video entry arriving again over the live event stream) cannot
  // overwrite what the user just picked. Whoever embeds this persists the reported selection
  // when its own action runs (saving the video's settings, starting the calibration), see
  // applyLensProfileSelection in usePluginParams.js.
  modelValue: {
    type: Object,
    default: null,
  },
});

const emit = defineEmits(["update:modelValue"]);

const videoId = computed(() => props.video?.id ?? null);
const videoReady = computed(() => !!(props.video?.width && props.video?.height));

// What is browsed (brand/model/aspect-ratio switch) and what is picked. Both are only ever
// written by the handlers below -- every change the user makes goes through exactly one of them,
// which also decides what happens to the selection, so there is no watcher that could re-sync
// the picker from somewhere else behind the user's back.
const brand = ref(null);
const model = ref(null);
const showIncompatible = ref(false);
const selection = ref({ lensProfileId: null, lensCrop: 1.0 });

const NOTHING_PICKED = { lensProfileId: null, lensCrop: 1.0 };

const commit = (next) => {
  selection.value = next;
  emit("update:modelValue", { ...next });
};

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

// The browsed list first: those entries were fetched for this video, so their per-video fields
// (recording modes, aspect fit) are the ones that apply. `byId` is the fallback for the assigned
// profile right after opening, before its brand's list has arrived.
const profileById = (id) =>
  lensProfileStore.profiles.find((entry) => entry.id === id) ?? lensProfileStore.byId[id] ?? null;

const selectedProfile = computed(() =>
  selection.value.lensProfileId ? profileById(selection.value.lensProfileId) : null
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

// A profile's recording modes come sorted with the plausible ones first (the video's own aspect
// ratio, largest crop), so the first is the default; a crop the newly picked profile still
// offers is kept.
const cropFor = (profile, currentCrop) => {
  const modes = profile?.recording_modes ?? [];
  if (modes.some((mode) => mode.crop === currentCrop)) return currentCrop;
  return modes.length > 0 ? modes[0].crop : 1.0;
};

const selectBrand = async (value) => {
  brand.value = value ?? null;
  model.value = null;
  // The picked profile belongs to the brand that was just left, and the select below no longer
  // lists it. Dropping it here is what makes the picker say what it will actually do: it used to
  // stay behind an empty-looking select and was then saved again as if nothing had been changed.
  commit({ ...NOTHING_PICKED });
  await lensProfileStore.fetchModels({ brand: brand.value });
  await loadProfiles();
};

const selectModel = async (value) => {
  model.value = value ?? null;
  // Same as for the brand: another camera model means other profiles, so the picked one goes.
  commit({ ...NOTHING_PICKED });
  await loadProfiles();
};

const toggleIncompatible = async (value) => {
  showIncompatible.value = !!value;
  const entries = await loadProfiles();
  // Narrowing back to this video's aspect ratio can drop the picked profile from the list.
  if (
    brand.value &&
    selection.value.lensProfileId &&
    !entries.some((entry) => entry.id === selection.value.lensProfileId)
  ) {
    commit({ ...NOTHING_PICKED });
  }
};

const selectProfile = (value) => {
  if (!value) {
    commit({ ...NOTHING_PICKED });
    return;
  }
  commit({
    lensProfileId: value,
    lensCrop: cropFor(profileById(value), selection.value.lensCrop),
  });
};

const selectCrop = (value) => {
  commit({ lensProfileId: selection.value.lensProfileId, lensCrop: value ?? 1.0 });
};

onMounted(async () => {
  // The video's own assignment is the starting point, and it is reported upwards right away: the
  // host's pending selection is then never "undefined", so starting a calibration run without
  // touching this picker saves exactly what the video already carries.
  commit({
    lensProfileId: props.video?.lens_profile_id ?? null,
    lensCrop: props.video?.lens_crop ?? 1.0,
  });

  // The lists are the browsing state of whichever picker is open; a previous one's results (for
  // another video, another brand) must not be read as this one's.
  lensProfileStore.reset();
  lensProfileStore.fetchBrands();

  const assignedId = selection.value.lensProfileId;
  if (!assignedId) return;
  // Always fetched for *this* video, so the recording modes and the aspect fit shown for the
  // assigned profile are the ones that apply to it.
  const assigned = await lensProfileStore.fetchProfile({ id: assignedId, videoId: videoId.value });
  if (!assigned) return;
  // Start out on the assigned profile's camera, so its own select shows it and switching to a
  // neighbouring profile or another recording mode needs no searching.
  brand.value = assigned.brand;
  model.value = assigned.model;
  // A profile calibrated at another aspect ratio is only listed with the switch on -- if the
  // video is assigned one, the switch starts on, or its own select would come up empty.
  if (assigned.compatible === false) showIncompatible.value = true;
  await lensProfileStore.fetchModels({ brand: assigned.brand });
  await loadProfiles();
});
</script>
