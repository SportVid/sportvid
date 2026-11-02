import { defineStore } from "pinia";
import { ref } from "vue";
import axios from "../plugins/axios";
import config from "../../app.config";

// Gyroflow lens profiles imported into the backend (management command import_lens_profiles),
// browsed brand -> model -> profile. Everything here is read-only reference data except
// setForVideo, which assigns a profile to a video; calibration_static_dlt then undistorts the
// clicked points with it (see the backend task's lens_intrinsics).
export const useLensProfileStore = defineStore("lens_profile", () => {
  const isLoading = ref(false);
  // [{ brand, group, num_profiles }] -- `group` is the camera family the profile was filed
  // under in the repository (GoPro, DJI, Mobile phones), shown to disambiguate same-named brands.
  const brands = ref([]);
  // [{ model, num_profiles }] of the currently browsed brand
  const models = ref([]);
  // profiles of the currently browsed brand/model, each with the per-video fields the list
  // endpoint adds for a ?video_id=: "compatible", "aspect_fit", "recording_modes"
  const profiles = ref([]);
  // profiles fetched by id (e.g. the one a video is already assigned), so showing the current
  // assignment doesn't require browsing to its brand first
  const byId = ref({});

  const fetchBrands = async () => {
    try {
      const res = await axios.get(`${config.API_LOCATION}/lens_profile/brands`);
      if (res.data.status === "ok") {
        brands.value = res.data.entries;
      }
      return brands.value;
    } catch (error) {
      console.error("Failed to list lens profile brands:", error);
      return [];
    }
  };

  const fetchModels = async ({ brand }) => {
    if (!brand) {
      models.value = [];
      return models.value;
    }
    try {
      const res = await axios.get(`${config.API_LOCATION}/lens_profile/models`, {
        params: { brand },
      });
      models.value = res.data.status === "ok" ? res.data.entries : [];
      return models.value;
    } catch (error) {
      console.error("Failed to list lens profile models:", error);
      models.value = [];
      return models.value;
    }
  };

  // `compatibleOnly` drops the profiles calibrated at another aspect ratio than the video's --
  // they can be applied (as a centred crop) but are the less safe choice, so the picker asks
  // for them explicitly.
  const fetchProfiles = async ({ brand, model, videoId, compatibleOnly = true }) => {
    if (!brand) {
      profiles.value = [];
      return profiles.value;
    }
    isLoading.value = true;
    try {
      const params = { brand };
      if (model) params.model = model;
      if (videoId) params.video_id = videoId;
      if (compatibleOnly) params.compatible_only = true;
      const res = await axios.get(`${config.API_LOCATION}/lens_profile/list`, { params });
      profiles.value = res.data.status === "ok" ? res.data.entries : [];
      for (const entry of profiles.value) {
        byId.value[entry.id] = entry;
      }
      return profiles.value;
    } catch (error) {
      console.error("Failed to list lens profiles:", error);
      profiles.value = [];
      return profiles.value;
    } finally {
      isLoading.value = false;
    }
  };

  const fetchProfile = async ({ id, videoId }) => {
    if (!id) return null;
    try {
      const params = { id };
      if (videoId) params.video_id = videoId;
      const res = await axios.get(`${config.API_LOCATION}/lens_profile/get`, { params });
      if (res.data.status !== "ok") return null;
      byId.value[res.data.entry.id] = res.data.entry;
      return res.data.entry;
    } catch (error) {
      console.error("Failed to get lens profile:", error);
      return null;
    }
  };

  // Assigns a profile to a video (null clears it); `lensCrop` is the EIS crop of the recording
  // mode the video was shot in. Returns the raw response: on refusal its "type" names why
  // (unsupported_lens_profile, incompatible_resolution, invalid_lens_crop), which the picker
  // shows. Existing calibrations keep the lens they were computed with -- they have to be rerun.
  const setForVideo = async ({ videoId, lensProfileId, lensCrop = 1.0 }) => {
    if (!videoId) return { status: "error" };
    isLoading.value = true;
    try {
      const res = await axios.post(`${config.API_LOCATION}/video/lens_profile/set`, {
        video_id: videoId,
        lens_profile_id: lensProfileId ?? null,
        lens_crop: lensProfileId ? lensCrop : null,
      });
      return res.data;
    } catch (error) {
      console.error("Failed to set the video's lens profile:", error);
      return { status: "error" };
    } finally {
      isLoading.value = false;
    }
  };

  return {
    isLoading,
    brands,
    models,
    profiles,
    byId,
    fetchBrands,
    fetchModels,
    fetchProfiles,
    fetchProfile,
    setForVideo,
  };
});
