import { ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { usePlayerStore } from "@/stores/player";
import { usePositionDataStore } from "@/stores/position_data";
import { usePluginRunStore } from "@/stores/plugin_run";

export function bytetrackParams() {
  const { t } = useI18n();
  const playerStore = usePlayerStore();

  const parameters = ref([
    {
      field: "slider",
      min: 1,
      max: 30,
      value: Math.round(playerStore.videoFPS),
      step: 1,
      name: "fps",
      text: t("modal.plugin.fps"),
      dataTour: "bytetrack-fps",
    },
  ]);

  return { parameters, optionalParameters: ref([]) };
}

export function dltParams() {
  const { t } = useI18n();

  const parameters = ref([
    {
      field: "select_calibration",
      name: "calibration_id",
      value: "",
      text: t("modal.plugin.calibration_static_dlt.calibration_id"),
      hint: t("modal.plugin.calibration_static_dlt.calibration_id_hint"),
    },
  ]);

  return { parameters, optionalParameters: ref([]) };
}

export function kpiComputationParams() {
  const { t } = useI18n();
  const positionDataStore = usePositionDataStore();

  const parameters = ref([
    {
      field: "select_options",
      name: "format",
      value: "kinexon",
      items: [
        ...positionDataStore.provider.map((p) => ({ title: p.name, value: p.id })),
        { title: "SportVid (ByteTrack)", value: "sportvid" },
      ],
      text: t("modal.plugin.kpi_computation.format"),
      dataTour: "kpi-format",
    },
    {
      field: "select_tracking_data",
      name: "tracking_data_id",
      value: "",
      text: t("modal.plugin.kpi_computation.tracking_data_id"),
      hint: t("modal.plugin.kpi_computation.tracking_data_id_hint"),
      format_filter: "kinexon",
      dataTour: "kpi-tracking-data",
    },
    {
      field: "select_bytetrack_run",
      name: "bytetrack_run_id",
      value: "",
      text: t("modal.plugin.kpi_computation.bytetrack_run_id"),
      hint: t("modal.plugin.kpi_computation.bytetrack_run_id_hint"),
      hidden: true,
      dataTour: "kpi-bytetrack-run",
    },
    {
      field: "select_calibration",
      name: "calibration_id",
      value: "",
      text: t("modal.plugin.kpi_computation.calibration_id"),
      hint: t("modal.plugin.kpi_computation.calibration_id_hint"),
      hidden: true,
      dlt: true,
      dataTour: "kpi-calibration",
    },
  ]);

  const optionalParameters = ref([
    {
      field: "select_options",
      name: "filter_type",
      value: "",
      items: [
        { title: t("modal.plugin.kpi_computation.filter_none"), value: "" },
        {
          title: t("modal.plugin.kpi_computation.filter_butterworth"),
          value: "butterworth_lowpass",
        },
        { title: t("modal.plugin.kpi_computation.filter_savgol"), value: "savgol_lowpass" },
      ],
      text: t("modal.plugin.kpi_computation.filter_type"),
      dataTour: "kpi-filter-type",
    },
    {
      field: "slider",
      name: "order",
      value: 3,
      min: 1,
      max: 10,
      step: 1,
      text: t("modal.plugin.kpi_computation.order"),
      hidden: true,
    },
    {
      field: "slider",
      name: "Wn",
      value: 1.0,
      min: 0.01,
      max: 10.0,
      step: 0.01,
      text: t("modal.plugin.kpi_computation.Wn"),
      hidden: true,
    },
    {
      field: "slider",
      name: "window_length",
      value: 5,
      min: 3,
      max: 51,
      step: 2,
      text: t("modal.plugin.kpi_computation.window_length"),
      hidden: true,
    },
    {
      field: "slider",
      name: "poly_order",
      value: 3,
      min: 1,
      max: 10,
      step: 1,
      text: t("modal.plugin.kpi_computation.poly_order"),
      hidden: true,
    },
  ]);

  // Toggle visibility of filter hyperparameters based on selected filter_type
  watch(
    () => optionalParameters.value.find((p) => p.name === "filter_type")?.value,
    (filterType) => {
      for (const p of optionalParameters.value) {
        if (p.name === "order" || p.name === "Wn") {
          p.hidden = filterType !== "butterworth_lowpass";
        } else if (p.name === "window_length" || p.name === "poly_order") {
          p.hidden = filterType !== "savgol_lowpass";
        }
      }
    },
    { immediate: true }
  );

  // Toggle tracking_data_id / bytetrack_run_id / calibration_id visibility based on format
  watch(
    () => parameters.value.find((p) => p.name === "format")?.value,
    (fmt) => {
      const trackingParam = parameters.value.find((p) => p.name === "tracking_data_id");
      const bytetrackParam = parameters.value.find((p) => p.name === "bytetrack_run_id");
      const calibrationParam = parameters.value.find((p) => p.name === "calibration_id");
      if (trackingParam) {
        trackingParam.hidden = fmt === "sportvid";
        trackingParam.format_filter = fmt !== "sportvid" ? fmt : null;
        trackingParam.value = "";
      }
      if (bytetrackParam) bytetrackParam.hidden = fmt !== "sportvid";
      if (calibrationParam) calibrationParam.hidden = fmt !== "sportvid";
    },
    { immediate: true }
  );

  return { parameters, optionalParameters };
}

export function submitPlugin(plugin, parameters, videoId) {
  const pluginRunStore = usePluginRunStore();
  const mappedParameters = parameters.map((p) =>
    "file" in p ? { name: p.name, file: p.file } : { name: p.name, value: p.value }
  );
  return pluginRunStore.submit({ plugin, parameters: mappedParameters, videoId });
}
