<template>
  <div>
    <div class="text-caption text-grey mb-1">
      {{ $t("calibration_asset.calibration.heading") }}
    </div>

    <!-- One click picks both: the asset this list belongs to, and the calibration of it that
         everything downstream should use. The active one is marked, but every row is a target --
         picking the one that already is active just selects the asset. -->
    <v-list-item
      v-for="calibration in calibrations"
      :key="calibration.id"
      density="compact"
      class="calibration-item px-2"
      @click.stop="emit('select', calibration)"
    >
      <template #prepend>
        <v-icon size="small" :color="isActive(calibration) ? 'primary' : undefined">
          {{ isActive(calibration) ? "mdi-radiobox-marked" : "mdi-radiobox-blank" }}
        </v-icon>
      </template>
      <v-list-item-title class="text-caption">
        {{ lensLabel(calibration) }}
        <!-- A lens_solve run that found no usable lens and fell back to a fit on the raw clicks -->
        <v-tooltip v-if="calibration.lens_notice" location="top" max-width="360">
          <template #activator="{ props: tooltipProps }">
            <v-icon v-bind="tooltipProps" size="x-small" color="warning" class="ml-1">
              mdi-alert-outline
            </v-icon>
          </template>
          <div>{{ $t("calibration_asset.calibration.lens_notice") }}</div>
          <div v-if="noticeReason(calibration)" class="mt-1">
            {{ $t("calibration_asset.calibration.lens_notice_reason", { reason: noticeReason(calibration) }) }}
          </div>
        </v-tooltip>
      </v-list-item-title>
      <v-list-item-subtitle class="text-caption">
        {{ detailsLabel(calibration) }}
      </v-list-item-subtitle>
    </v-list-item>

    <!-- An asset nothing has run on yet: still selectable, there is just nothing to pick between -->
    <v-list-item
      v-if="!calibrations.length"
      density="compact"
      class="calibration-item px-2"
      @click.stop="emit('select', null)"
    >
      <template #prepend>
        <v-icon size="small">mdi-radiobox-blank</v-icon>
      </template>
      <v-list-item-title class="text-caption">
        {{ $t("calibration_asset.calibration.none") }}
      </v-list-item-title>
    </v-list-item>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { useI18n } from "vue-i18n";

const { t, te } = useI18n();

const props = defineProps({
  // a calibration asset entry as the list endpoint returns it (needs "calibrations" and
  // "active_calibration_id")
  asset: {
    type: Object,
    default: null,
  },
});

// The calibration to use, or null for "this asset has none yet". Activating it and loading the
// asset is the host's business -- this only names what was picked.
const emit = defineEmits(["select"]);

const calibrations = computed(() => props.asset?.calibrations ?? []);

// What distinguishes the calibrations of one asset is the lens they were fitted with -- which is
// also where a lens_solve run that fell back to a plain fit becomes visible.
const lensLabel = (calibration) => {
  if (calibration.lens_model === "angular") return t("calibration_asset.calibration.lens_solved");
  if (calibration.lens_model) {
    return t("calibration_asset.calibration.lens_profile", {
      name: calibration.lens_profile_name ?? calibration.lens_model,
    });
  }
  return t("calibration_asset.calibration.no_lens");
};

// Why no lens was used, from the calibration's lens_notice {type, message, details} -- the same
// shape and codes as a run's failure_reason, so the same translations apply (see ModalStatus.vue).
// The solver's own explanation (details.reason) is only available in English.
const noticeReason = (calibration) => {
  const notice = calibration.lens_notice;
  if (!notice) return null;
  const key = `modal.plugin.failure.${notice.type}`;
  const text = te(key) ? t(key, notice.details || {}) : notice.message;
  const reason = notice.details?.reason;
  return reason ? `${text} (${reason})` : text;
};

const detailsLabel = (calibration) => {
  const date = new Date(calibration.date).toLocaleString();
  const error =
    calibration.reprojection_error != null
      ? t("calibration_asset.calibration.error", {
          value: calibration.reprojection_error.toFixed(2),
        })
      : t("calibration_asset.calibration.error_unknown");
  return `${date} · ${error}`;
};

const isActive = (calibration) => props.asset?.active_calibration_id === calibration.id;
</script>

<style scoped>
.calibration-item {
  min-height: 34px;
}
</style>
