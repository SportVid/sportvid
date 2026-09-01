<template>
  <div ref="videoContainer" class="d-flex flex-column pa-4">
    <div class="card-header-zone">
      <div class="video-title">{{ playerStore.videoName }}</div>
    </div>

    <v-row justify="center" class="video-row">
      <Teleport to="body" :disabled="!isPip">
        <div
          ref="videoFullscreenRoot"
          class="video-fullscreen-root"
          :class="{ 'pip-panel': isPip }"
          :style="isPip ? pipPanelStyle : null"
        >
          <div
            class="video-wrapper"
            :class="{ 'pip-content': isPip }"
            @mouseenter="hovering = true"
            @mouseleave="hovering = false"
            @pointerdown="onPipDragStart"
          >
            <video
              ref="videoElement"
              @play="onPlay"
              @pause="onPause"
              @ended="onEnded"
              @timeupdate="onTimeUpdate"
              @loadedmetadata="updateVideoSize"
              :style="
                isVideoFullscreen
                  ? {
                      maxHeight: 100 + 'vh',
                    }
                  : isPip
                  ? {
                      width: '100%',
                      height: '100%',
                      objectFit: 'contain',
                    }
                  : {
                      maxHeight: maxVideoHeight * 100 + 'vh',
                      maxWidth: '100%',
                    }
              "
            />

            <v-icon
              v-if="!isPip"
              class="fullscreen-toggle"
              @click="toggleVideoFullscreen"
              :class="{ visible: hovering }"
            >
              {{ isVideoFullscreen ? "mdi-fullscreen-exit" : "mdi-fullscreen" }}
            </v-icon>

            <!-- Enter-PiP trigger, next to the fullscreen icon; only shown
                 outside PiP. Kept as its own button rather than swapped via
                 v-if/else with the close button below, since the two live in
                 different corner slots once in PiP (fullscreen-toggle isn't
                 rendered any more, so the close button can move all the way
                 into the actual corner). -->
            <v-icon
              v-if="!isPip"
              class="pip-toggle"
              @click="openPip"
              @pointerdown.stop
              :class="{ visible: hovering }"
              :title="$t('pip.enter')"
            >
              mdi-picture-in-picture-top-right
            </v-icon>

            <!-- Dedicated close button shown only inside the PiP panel,
                 flush in the actual top-right corner. -->
            <v-icon
              v-if="isPip"
              class="pip-close-button"
              @click="closePip"
              @pointerdown.stop
              :title="$t('pip.exit')"
            >
              mdi-close
            </v-icon>

            <div
              v-if="isVideoFullscreen || isPip"
              class="fullscreen-controls pip-no-drag"
              :class="{ visible: hovering || isPip }"
            >
              <div class="controls-top">
                <v-icon @click="togglePlaying" class="control-icon">
                  <template v-if="videoEnded">mdi-restart</template>
                  <template v-else-if="videoPlaying">mdi-pause</template>
                  <template v-else>mdi-play</template>
                </v-icon>
                <div class="time-code">{{ getTimecode(playerStore.currentTime) }}</div>
                <v-icon v-if="isPip" @click="playerStore.toggleMute" class="control-icon ml-auto">
                  {{ playerStore.isMuted ? "mdi-volume-mute" : playerStore.volumeIcon }}
                </v-icon>
              </div>

              <v-slider
                v-model="progress"
                @update:model-value="onProgressChange"
                hide-details
                color="white"
                :thumb-size="15"
                :step="1000 / playerStore.videoFPS"
                min="0"
                :max="playerStore.videoDuration"
              />
            </div>

            <!-- DEBUG: plain rectangular bounding box, using the same x/y/w/h
          indices (position[5..8]) as getEllipseSvg. Handy to sanity-check the
          ellipse placement against the actual box again if it's ever revisited.
          Kept but disabled. -->
            <!-- <div
            v-for="position in bboxesStore.bboxDataInterpolated[currentFrameKey]"
            v-show="bboxesStore.showBoundingBox"
            :key="`rect-${position[0]}`"
            :style="getBBoxRectStyle(position)"
          ></div> -->

            <div
              v-for="position in visibleBboxPositions"
              v-show="bboxesStore.showBoundingBox"
              :key="position"
              class="pip-no-drag"
              :style="getEllipseSvg(position).style"
            >
              <svg class="player-ellipse" :viewBox="getEllipseSvg(position).viewBox">
                <path
                  :d="getEllipseSvg(position).arc"
                  :stroke="getEllipseSvg(position).color"
                  stroke-width="2"
                  fill="none"
                  stroke-linecap="round"
                />
              </svg>
              <v-tooltip
                activator="parent"
                location="top"
                class="bounding-box-tooltip"
                :style="{
                  '--tooltip-bg': toRgb(visualizationStore.getTeamColor(position[1]), 0.7),
                }"
                interactive
              >
                <div>
                  <div>
                    <strong
                      >{{ $t("modal.bounding_box.tooltip.box_id") }}:
                      {{ `${currentFrameKey}-${position[0]}` }}</strong
                    >
                  </div>
                  <v-divider class="my-1" />
                  <div>
                    {{ entityLabelKey(position[1]) }}:
                    {{ topViewStore.getEntityName(position[0], position[1]) }}
                  </div>
                  <div>{{ $t("modal.bounding_box.tooltip.team_id") }}: {{ position[1] }}</div>
                </div>
              </v-tooltip>
              <div
                v-show="bboxesStore.showPlayerId"
                class="bounding-box-player-id"
                :style="{
                  ...getEllipseSvg(position).labelStyle,
                  color: visualizationStore.getTeamColor(position[1]),
                }"
              >
                {{ topViewStore.getEntityNumber(position[0], position[1]) }}
              </div>
            </div>

            <!-- <div
          v-for="o in calibrationAssetStore.filteredVideoObject"
          v-show="calibrationAssetStore.showVideoAsset"
          :key="o.id"
          :style="{
            position: 'absolute',
            width: '12px',
            height: '12px',
            backgroundColor: 'red',
            borderRadius: '50%',
            transform: 'translate(-50%, -50%)',
            top: isVideoFullscreen
              ? videoSize.top + o.videoCoordsRel.y * videoSize.height + 'px'
              : o.videoCoordsRel.y * videoSize.height + 'px',
            left: isVideoFullscreen
              ? videoSize.left + o.videoCoordsRel.x * videoSize.width + 'px'
              : o.videoCoordsRel.x * videoSize.width + 'px',
          }"
          @mouseenter="calibrationAssetStore.hoveredVideoObject = o.id"
          @mouseleave="calibrationAssetStore.hoveredVideoObject = null"
        /> -->
            <svg
              :width="videoSize.width"
              :height="videoSize.height"
              style="position: absolute; top: 0; left: 0; pointer-events: none"
            >
              <template v-for="o in calibrationAssetStore.filteredVideoObject">
                <circle
                  v-if="o.videoCoordsRel.length === 1"
                  v-show="calibrationAssetStore.showVideoAsset"
                  :key="o.id"
                  :cx="o.videoCoordsRel[0].x * videoSize.width"
                  :cy="o.videoCoordsRel[0].y * videoSize.height"
                  r="6"
                  :fill="calibrationAssetStore.objectColorMap[o.id] ?? 'red'"
                  fill-opacity="0.8"
                  style="pointer-events: all"
                  @mouseenter="calibrationAssetStore.hoveredVideoObject = o.id"
                  @mouseleave="calibrationAssetStore.hoveredVideoObject = null"
                />

                <line
                  v-if="o.videoCoordsRel.length === 2"
                  v-show="calibrationAssetStore.showVideoAsset"
                  :key="o.id"
                  :x1="o.videoCoordsRel[0].x * videoSize.width"
                  :y1="o.videoCoordsRel[0].y * videoSize.height"
                  :x2="o.videoCoordsRel[1].x * videoSize.width"
                  :y2="o.videoCoordsRel[1].y * videoSize.height"
                  stroke-width="4"
                  :stroke="calibrationAssetStore.objectColorMap[o.id] ?? 'red'"
                  stroke-opacity="0.8"
                  fill="none"
                  style="pointer-events: all"
                  @mouseenter="calibrationAssetStore.hoveredVideoObject = o.id"
                  @mouseleave="calibrationAssetStore.hoveredVideoObject = null"
                />

                <path
                  v-if="o.videoCoordsRel.length > 2"
                  v-show="calibrationAssetStore.showVideoAsset"
                  :key="o.id"
                  :d="
                    (() => {
                      const points = o.videoCoordsRel.map((p) => ({
                        x: p.x * videoSize.width,
                        y: p.y * videoSize.height,
                      }));
                      let d = `M ${points[0].x} ${points[0].y}`;
                      for (let i = 1; i < points.length; i++) {
                        d += ` L ${points[i].x} ${points[i].y}`;
                      }
                      return d;
                    })()
                  "
                  :stroke="calibrationAssetStore.objectColorMap[o.id] ?? 'red'"
                  stroke-width="4"
                  stroke-opacity="0.8"
                  fill="none"
                  style="pointer-events: all"
                  @mouseenter="calibrationAssetStore.hoveredVideoObject = o.id"
                  @mouseleave="calibrationAssetStore.hoveredVideoObject = null"
                />
              </template>
            </svg>

            <svg
              :width="videoSize.width"
              :height="videoSize.height"
              style="position: absolute; top: 0; left: 0; pointer-events: none"
            >
              <template v-for="o in calibrationAssetStore.videoObjectReprojection">
                <circle
                  v-if="o.length === 1"
                  v-show="calibrationAssetStore.showVideoAsset"
                  :key="o.id"
                  :cx="o[0].x * videoSize.width + 'px'"
                  :cy="o[0].y * videoSize.height + 'px'"
                  r="3"
                  fill="blue"
                  style="pointer-events: none"
                />

                <line
                  v-if="o.length === 2"
                  v-show="calibrationAssetStore.showVideoAsset"
                  :key="o.id"
                  :x1="o[0].x * videoSize.width + 'px'"
                  :y1="o[0].y * videoSize.height + 'px'"
                  :x2="o[1].x * videoSize.width + 'px'"
                  :y2="o[1].y * videoSize.height + 'px'"
                  stroke-width="3"
                  stroke="blue"
                  fill="none"
                  style="pointer-events: none"
                />

                <path
                  v-if="o.length > 2"
                  v-show="calibrationAssetStore.showVideoAsset"
                  :key="o.id"
                  :d="
                    (() => {
                      const points = o.map((p) => ({
                        x: p.x * videoSize.width,
                        y: p.y * videoSize.height,
                      }));
                      let d = `M ${points[0].x} ${points[0].y}`;
                      for (let i = 1; i < points.length; i++) {
                        d += ` L ${points[i].x} ${points[i].y}`;
                      }
                      return d;
                    })()
                  "
                  stroke="blue"
                  stroke-width="3"
                  fill="none"
                  style="pointer-events: none"
                />
              </template>
            </svg>

            <v-icon v-if="isPip" class="pip-resize-handle" @pointerdown.stop="onPipResizeStart">
              mdi-resize-bottom-right
            </v-icon>
          </div>
        </div>
      </Teleport>

      <div
        v-if="isPip"
        class="pip-placeholder"
        :style="{ height: (lastCardVideoHeight || 200) + 'px' }"
      >
        <v-icon size="40" class="pip-placeholder-icon">mdi-picture-in-picture-top-right</v-icon>
        <div class="pip-placeholder-text">{{ $t("video_player.pip.playing_in_pip") }}</div>
        <v-btn size="small" variant="flat" color="primary" @click="closePip">
          {{ $t("pip.return_to_card") }}
        </v-btn>
      </div>
    </v-row>

    <div style="position: relative">
      <v-row ref="videoControl" class="video-control mt-6">
        <v-btn @click="deltaSeek(-1)" size="small">
          <v-icon>mdi-skip-backward</v-icon>
        </v-btn>

        <v-btn @click="stepBackwardFrame" size="small">
          <v-icon>mdi-skip-previous</v-icon>
        </v-btn>

        <v-btn @click="togglePlaying" size="small">
          <v-icon v-if="videoEnded">mdi-restart</v-icon>
          <v-icon v-else-if="videoPlaying">mdi-pause</v-icon>
          <v-icon v-else>mdi-play</v-icon>
        </v-btn>

        <v-btn @click="stepForwardFrame" size="small">
          <v-icon> mdi-skip-next</v-icon>
        </v-btn>

        <v-btn @click="deltaSeek(1)" size="small">
          <v-icon> mdi-skip-forward</v-icon>
        </v-btn>

        <div class="time-code flex-grow-1 flex-shrink-0 ml-2">
          {{ getTimecode(playerStore.currentTime) }}
        </div>

        <v-menu location="top">
          <template #activator="{ props }">
            <v-btn v-bind="props" size="small" data-tour="video-display-settings-btn">
              <v-icon>mdi-menu</v-icon>
            </v-btn>
          </template>
          <v-list
            class="py-0"
            density="compact"
            width="190px"
            data-tour="video-display-settings-list"
          >
            <v-list-item
              class="menu-item"
              @click="bboxesStore.viewBoundingBox"
              :disabled="noBboxData"
            >
              <v-list-item-title class="d-flex justify-space-between">
                {{ $t("position_data.display_settings.view_bounding_box") }}
                <tab-window-icon
                  :class="{
                    'text-disabled': !bboxesStore.showBoundingBox || noBboxData,
                    'text-red': bboxesStore.showBoundingBox,
                  }"
                >
                  mdi-check
                </tab-window-icon>
              </v-list-item-title>
            </v-list-item>

            <v-list-item class="menu-item" @click="bboxesStore.viewPlayerId" :disabled="noBboxData">
              <v-list-item-title class="d-flex justify-space-between">
                {{ $t("position_data.display_settings.view_player_id") }}
                <tab-window-icon
                  :class="{
                    'text-disabled': !bboxesStore.showPlayerId || noBboxData,
                    'text-red': bboxesStore.showPlayerId,
                  }"
                >
                  mdi-check
                </tab-window-icon>
              </v-list-item-title>
            </v-list-item>

            <v-list-item
              class="menu-item"
              @click="showModalToggleEntities = true"
              :disabled="noBboxData"
            >
              <v-list-item-title class="d-flex justify-space-between">
                {{ $t("position_data.display_settings.toggle_entities") }}
              </v-list-item-title>
            </v-list-item>

            <v-list-item
              class="menu-item"
              @click="showModalPositionDataEntityColors = true"
              :disabled="noBboxData"
            >
              <v-list-item-title class="d-flex justify-space-between">
                {{ $t("position_data.display_settings.entity_colors") }}
              </v-list-item-title>
            </v-list-item>

            <v-divider />

            <v-menu location="end" open-on-hover>
              <template #activator="{ props }">
                <v-list-item v-bind="props" class="menu-item">
                  <v-list-item-title class="d-flex justify-space-between">
                    {{ $t("position_data.display_settings.position_data.title") }}
                    <tab-window-icon>mdi-chevron-right</tab-window-icon>
                  </v-list-item-title>
                </v-list-item>
              </template>
              <v-list class="py-0" density="compact">
                <!-- Drops the current selection (bbox overlay + everything derived from it) so
                     the TopView/Heatmap/KPI cards fall back to their own PositionDataMenu --
                     lets the user generate a fresh run right away instead of having to go back
                     to VideoView and reopen the video just to get back to that empty state. -->
                <v-list-item
                  v-if="canWrite"
                  class="menu-item"
                  @click="positionDataStore.resetPositionData()"
                >
                  <v-list-item-title>
                    {{ $t("position_data.display_settings.position_data.create_new") }}
                  </v-list-item-title>
                </v-list-item>
                <v-list-item
                  v-if="canWrite"
                  class="menu-item"
                  @click="showModalPositionDataUpload = true"
                >
                  <v-list-item-title>
                    {{ $t("position_data.display_settings.position_data.upload") }}
                  </v-list-item-title>
                </v-list-item>
                <v-list-item class="menu-item" @click="showModalPositionDataSelect = true">
                  <v-list-item-title>
                    {{ $t("position_data.display_settings.position_data.select") }}
                  </v-list-item-title>
                </v-list-item>
              </v-list>
            </v-menu>
          </v-list>
        </v-menu>
        <ModalPositionDataUpload
          v-if="showModalPositionDataUpload"
          v-model="showModalPositionDataUpload"
        />
        <ModalPositionDataSelect
          v-if="showModalPositionDataSelect"
          v-model="showModalPositionDataSelect"
        />
        <ModalPositionDataEntityColors
          v-if="showModalPositionDataEntityColors"
          v-model="showModalPositionDataEntityColors"
        />

        <v-menu offset-y top>
          <template #activator="{ props }">
            <v-btn v-bind="props" size="small">
              {{ currentSpeed.title }}
            </v-btn>
          </template>
          <v-list>
            <v-list-item v-for="(item, index) in speeds" :key="item" class="speed-item">
              <v-list-item-title v-on:click="onSpeedChange(index)">
                {{ item.title }}
              </v-list-item-title>
            </v-list-item>
          </v-list>
        </v-menu>

        <v-btn @click="playerStore.toggleMute" size="small">
          <v-icon>{{ playerStore.isMuted ? "mdi-volume-mute" : playerStore.volumeIcon }}</v-icon>
        </v-btn>

        <div style="width: 13%; min-width: 80px">
          <v-slider
            v-model="playerStore.volume"
            @update:model-value="playerStore.changeVolume"
            max="100"
            min="0"
            hide-details
            color="primary"
            :thumb-size="15"
          />
        </div>
      </v-row>

      <v-row ref="videoSlider">
        <v-slider
          v-model="progress"
          @update:model-value="onProgressChange"
          hide-details
          color="primary"
          :thumb-size="15"
          :step="1000 / playerStore.videoFPS"
          min="0"
          :max="playerStore.videoDuration"
        />
      </v-row>

      <div v-if="showModalToggleEntities" class="players-toggle-overlay">
        <v-icon
          variant="tonal"
          color="error"
          size="small"
          class="players-toggle-close"
          @click="showModalToggleEntities = false"
        >
          mdi-close
        </v-icon>
        <div class="players-toggle-content">
          <div class="entity-kind-bar">
            <div
              v-for="kind in ENTITY_KINDS"
              :key="kind.key"
              class="entity-kind-chip"
              :class="{ active: bboxesStore.visibleEntityKinds[kind.key] }"
              @click="bboxesStore.toggleEntityKind(kind.key)"
            >
              {{ $t(kind.labelKey) }}
            </div>
          </div>
          <div
            v-for="(entities, teamId) in overlayTeamGroups"
            :key="teamId"
            class="chart-legend-team"
          >
            <div
              class="team-dot"
              :style="{
                backgroundColor: overlayIsTeamFullySelected(teamId)
                  ? toRgb(visualizationStore.getTeamColor(teamId), 0)
                  : 'transparent',
                color: overlayIsTeamFullySelected(teamId)
                  ? '#fff'
                  : toRgb(visualizationStore.getTeamColor(teamId), 0),
                borderColor: toRgb(visualizationStore.getTeamColor(teamId), 0),
              }"
              @click="overlayToggleTeam(teamId)"
            >
              <v-icon v-if="Number(teamId) === 0" size="14">mdi-soccer</v-icon>
              <template v-else>{{ overlayGetTeamName(teamId) }}</template>
            </div>
            <span class="chart-legend-sep">|</span>
            <div
              v-for="e in entities"
              :key="`${e.teamId}_${e.playerId}`"
              class="player-dot"
              :style="{
                backgroundColor: includedEntities.has(_entityInclusionKey(e.teamId, e.playerId))
                  ? toRgb(overlayEntityColors[`${e.teamId}_${e.playerId}`], 0)
                  : toRgb(overlayEntityColors[`${e.teamId}_${e.playerId}`], 0.6),
                color: includedEntities.has(_entityInclusionKey(e.teamId, e.playerId))
                  ? '#fff'
                  : '#222',
                borderColor: includedEntities.has(_entityInclusionKey(e.teamId, e.playerId))
                  ? toRgb(overlayEntityColors[`${e.teamId}_${e.playerId}`], 0)
                  : toRgb(overlayEntityColors[`${e.teamId}_${e.playerId}`], 0.6),
              }"
              @click="toggleEntityInclusion(_entityInclusionKey(e.teamId, e.playerId))"
            >
              {{ overlayGetEntityLabel(e.playerId, e.teamId) }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from "vue";
import { useI18n } from "vue-i18n";
import { usePictureInPicture } from "@/composables/usePictureInPicture";
import { usePlayerStore } from "@/stores/player";
import { useVideoStore } from "@/stores/video";
import { useCalibrationAssetStore } from "@/stores/calibration_asset";
import { useBboxesStore } from "@/stores/bboxes";
import { usePositionDataStore } from "@/stores/position_data";
import { useVisualizationStore } from "@/stores/visualization";
import { useTopViewStore } from "@/stores/top_view";
import { useUserStore } from "@/stores/user";
import { getTimecode } from "@/plugins/time";
import ModalPositionDataSelect from "@/components/position-data/ModalPositionDataSelect.vue";
import ModalPositionDataUpload from "@/components/position-data/ModalPositionDataUpload.vue";
import ModalPositionDataEntityColors from "@/components/position-data/ModalPositionDataEntityColors.vue";
import { toRgb } from "@/plugins/helpers";
import { useHlsVideo } from "@/composables/useHlsVideo";

const playerStore = usePlayerStore();
const videoStore = useVideoStore();
const calibrationAssetStore = useCalibrationAssetStore();
const bboxesStore = useBboxesStore();
const positionDataStore = usePositionDataStore();
const visualizationStore = useVisualizationStore();
const topViewStore = useTopViewStore();
const userStore = useUserStore();
const { t } = useI18n();

const canWrite = computed(() => {
  if (userStore.role === "admin") return true;
  const ownerUsername = playerStore.video?.owner_username;
  if (!ownerUsername) return true;
  return ownerUsername === userStore.username;
});

const showModalPositionDataSelect = ref(false);
const showModalPositionDataUpload = ref(false);
const showModalPositionDataEntityColors = ref(false);
const showModalToggleEntities = ref(false);

// Gates every display-settings item that acts on the box overlay itself (view/id/entities/
// colors) — with no bbox data loaded there's nothing for them to show or change. Position
// Data (select/upload) stays enabled since that's how you'd load some in the first place.
const noBboxData = computed(
  () => !bboxesStore.bboxDataActive || Object.keys(bboxesStore.bboxDataActive).length === 0
);

// Toggle bar for visible entity kinds + individual entity toggling on the video overlay.
// Roster (topViewStore.precomputed*List) is the shared entity list also used by TopView's
// own toggle-entities overlay, but the selection itself (includedEntities) and the kind
// filter (bboxesStore.visibleEntityKinds) are this card's own — see the comment on
// bboxesStore.showPlayerId for why video/top-view are kept independent here.
const ENTITY_KINDS = [
  { key: "player", labelKey: "position_data.entity_kind.player" },
  { key: "ref", labelKey: "position_data.entity_kind.ref" },
  { key: "ball", labelKey: "position_data.entity_kind.ball" },
  { key: "rest", labelKey: "position_data.entity_kind.rest" },
];

// Entity-inclusion keys are namespaced by *kind* (ball / ref / player), not by the exact
// team_id -- team_id 1 (rest) and 3+ (actual teams) all share the same person/"player_ids"
// id space on the backend (see _compute_meta_data's comment in bounding_boxes.py), so a
// player's key must stay stable across a team re-assignment. Without this, a per-frame team
// edit (the "single box" scope in BboxIdentityPanel.vue, which only touches one frame) makes that
// frame's box carry a team_id the aggregate-built includedEntities set never learned about
// (precomputedPlayerList is one team_id per player for the *whole* video), so the edited
// frame's box would silently disappear from visibleBboxPositions below.
const _entityInclusionKey = (teamId, playerId) => {
  const tid = Number(teamId);
  const kind = tid === 0 ? "ball" : tid === 2 ? "ref" : "player";
  return `${kind}_${playerId}`;
};

const includedEntities = ref(new Set());
const _buildAllEntitySet = () => {
  const ids = new Set();
  for (const p of topViewStore.precomputedPlayerList)
    ids.add(_entityInclusionKey(p.teamId, p.playerId));
  for (const p of topViewStore.precomputedRefList)
    ids.add(_entityInclusionKey(p.teamId, p.playerId));
  for (const p of topViewStore.precomputedBallList)
    ids.add(_entityInclusionKey(p.teamId, p.playerId));
  for (const p of topViewStore.precomputedInactiveList)
    ids.add(_entityInclusionKey(p.teamId, p.playerId));
  return ids;
};
watch(
  () => [
    topViewStore.precomputedPlayerList,
    topViewStore.precomputedRefList,
    topViewStore.precomputedBallList,
    topViewStore.precomputedInactiveList,
  ],
  () => {
    includedEntities.value = _buildAllEntitySet();
  },
  { immediate: true }
);
const toggleEntityInclusion = (id) => {
  const newSet = new Set(includedEntities.value);
  if (newSet.has(id)) {
    newSet.delete(id);
  } else {
    newSet.add(id);
  }
  includedEntities.value = newSet;
};

const overlayEntityOptions = computed(() => {
  const visible = bboxesStore.visibleEntityKinds;
  const lists = [];
  if (visible.player) lists.push(...topViewStore.precomputedPlayerList);
  if (visible.ref) lists.push(...topViewStore.precomputedRefList);
  if (visible.ball) lists.push(...topViewStore.precomputedBallList);
  if (visible.rest) lists.push(...topViewStore.precomputedInactiveList);
  return lists.sort((a, b) => a.teamId - b.teamId || a.playerId - b.playerId);
});

const overlayTeamGroups = computed(() => {
  const groups = {};
  for (const p of overlayEntityOptions.value) {
    if (!groups[p.teamId]) groups[p.teamId] = [];
    groups[p.teamId].push(p);
  }
  return groups;
});

const overlayEntityColors = computed(() => {
  const map = {};
  for (const p of overlayEntityOptions.value) {
    map[`${p.teamId}_${p.playerId}`] = visualizationStore.getTeamColor(p.teamId);
  }
  return map;
});

const overlayGetEntityLabel = (playerId, teamId) => {
  if (Number(teamId) === 0 || Number(teamId) === 2) return playerId;
  return topViewStore.getEntityNumber(playerId, teamId);
};

const overlayGetTeamName = (teamId) => topViewStore.getTeamDisplayName(teamId);

const overlayIsTeamFullySelected = (teamId) => {
  const teamKeys = (overlayTeamGroups.value[teamId] || []).map((p) =>
    _entityInclusionKey(p.teamId, p.playerId)
  );
  return teamKeys.length > 0 && teamKeys.every((key) => includedEntities.value.has(key));
};

const overlayToggleTeam = (teamId) => {
  const teamKeys = (overlayTeamGroups.value[teamId] || []).map((p) =>
    _entityInclusionKey(p.teamId, p.playerId)
  );
  const allSelected = teamKeys.every((key) => includedEntities.value.has(key));
  const newSet = new Set(includedEntities.value);
  if (allSelected) {
    teamKeys.forEach((key) => newSet.delete(key));
  } else {
    teamKeys.forEach((key) => newSet.add(key));
  }
  includedEntities.value = newSet;
};

// Entity-kind + individual-selection filtered view of the current frame's boxes. The
// showBoundingBox toggle (v-show in the template) is deliberately separate from this —
// it's "show boxes at all", this is "which ones".
const visibleBboxPositions = computed(() => {
  const positions = bboxesStore.bboxDataInterpolated[currentFrameKey.value];
  if (!positions) return [];
  const visible = bboxesStore.visibleEntityKinds;
  return positions.filter((position) => {
    const tid = position[1];
    const kind = tid === 0 ? "ball" : tid === 2 ? "ref" : tid === 1 ? "rest" : "player";
    if (!visible[kind]) return false;
    return includedEntities.value.has(_entityInclusionKey(tid, position[0]));
  });
});

const entityLabelKey = (teamId) => {
  const tid = Number(teamId);
  if (tid === 0) return t("modal.bounding_box.tooltip.ball_id");
  if (tid === 2) return t("modal.bounding_box.tooltip.ref_id");
  return t("modal.bounding_box.tooltip.player_id");
};

const videoContainer = ref(null);
const videoElement = ref(null);
onMounted(() => {
  if (videoElement.value) playerStore.videoElement = videoElement.value;
});

const lastReportedFrame = ref(null);
const onTimeUpdate = (event) => {
  const videoTimeMs = Math.round(event.target.currentTime * 1000);
  const frameMs = Math.round(1000 / (playerStore.videoFPS || 30));
  const closestFrame = Math.round(videoTimeMs / frameMs) * frameMs;
  if (lastReportedFrame.value !== closestFrame) {
    lastReportedFrame.value = closestFrame;
    playerStore.setCurrentTime(closestFrame);
  }
};
const deltaSeek = (delta) => {
  if (videoElement.value) {
    const newTime = videoElement.value.currentTime + delta;
    playerStore.setCurrentTime(newTime * 1000);
    videoElement.value.currentTime = newTime;
  }
};

function goToFrameMs(frameMs) {
  if (!videoElement.value) return;
  const timeSec = frameMs / 1000;
  videoElement.value.currentTime = timeSec;
  lastReportedFrame.value = frameMs;
  playerStore.setCurrentTime(frameMs);
}

function goToFrameIndex(frameIndex) {
  const frameMs = Math.round((frameIndex * 1000) / (playerStore.videoFPS || 30));
  goToFrameMs(frameMs);
}

function stepForwardFrame() {
  const frameMsLen = Math.round(1000 / (playerStore.videoFPS || 30));
  const current = Math.round(playerStore.currentTime / frameMsLen) * frameMsLen;
  goToFrameMs(current + frameMsLen);
}

function stepBackwardFrame() {
  const frameMsLen = Math.round(1000 / (playerStore.videoFPS || 30));
  const current = Math.round(playerStore.currentTime / frameMsLen) * frameMsLen;
  goToFrameMs(Math.max(0, current - frameMsLen));
}

const targetTime = computed(() => playerStore.targetTime);
const onProgressChange = (time) => {
  if (videoElement.value) {
    const targetTime = Math.round(time);
    progress.value = targetTime;
    playerStore.setCurrentTime(targetTime);
    videoElement.value.currentTime = targetTime / 1000;
  }
};
watch(targetTime, (newTargetTime) => {
  if (videoElement.value) {
    const rounded = Math.round(newTargetTime);
    progress.value = rounded;
    playerStore.setCurrentTime(rounded);
    // This was missing -- the watcher only ever updated the store's displayed
    // currentTime, never the actual <video> element, so every setTargetTime()
    // caller (jumpToEvent, EventsTimeline click/drag, Timeline.vue) moved the
    // timecode/playhead visually without the video itself seeking at all.
    videoElement.value.currentTime = rounded / 1000;
    lastReportedFrame.value = rounded;
  }
});

let updateTimer = null;
const MIN_INTERVAL_MS = 16;
const startUpdatingTime = () => {
  if (updateTimer) clearInterval(updateTimer);

  const frameMs = Math.max(Math.round(1000 / (playerStore.videoFPS || 30)), MIN_INTERVAL_MS);

  updateTimer = setInterval(() => {
    if (videoElement.value) {
      const videoTimeMs = Math.round(videoElement.value.currentTime * 1000);
      const roundedFrame = Math.round(videoTimeMs / frameMs) * frameMs;
      if (lastReportedFrame.value !== roundedFrame) {
        lastReportedFrame.value = roundedFrame;
        playerStore.setCurrentTime(roundedFrame);
      }
    }
  }, frameMs);
};
const stopUpdatingTime = () => {
  if (updateTimer) {
    clearInterval(updateTimer);
    updateTimer = null;
  }
};
onMounted(() => {
  startUpdatingTime();
});
onBeforeUnmount(() => {
  stopUpdatingTime();
});
watch(
  () => playerStore.playing,
  (isPlaying) => {
    if (isPlaying) {
      startUpdatingTime();
    } else {
      stopUpdatingTime();
    }
  }
);

const onPlay = () => {
  startUpdatingTime();
  playerStore.setEnded(false);
  playerStore.setPlaying(true);
};
const onPause = () => {
  stopUpdatingTime();
  playerStore.setPlaying(false);
};
const onEnded = () => {
  stopUpdatingTime();
  playerStore.setPlaying(false);
  playerStore.setEnded(true);
};

const progress = ref(0);
watch(
  () => playerStore.currentTime,
  (newTime) => {
    progress.value = newTime;
  }
);

watch(
  () => playerStore.volume,
  () => {
    if (playerStore.videoElement) {
      playerStore.videoElement.volume = playerStore.volume / 100;
    }
  }
);

const videoEnded = computed(() => playerStore.ended);
const videoPlaying = computed(() => playerStore.playing);
const togglePlaying = () => playerStore.togglePlaying();
watch(videoPlaying, (isPlaying) => {
  if (videoElement.value) {
    isPlaying ? videoElement.value.play() : videoElement.value.pause();
  }
});

const currentSpeed = ref({ title: "1.00", value: 1.0 });
const speeds = [
  { title: "0.25", value: 0.25 },
  { title: "0.50", value: 0.5 },
  { title: "0.75", value: 0.75 },
  { title: "1.00", value: 1.0 },
  { title: "1.25", value: 1.25 },
  { title: "1.50", value: 1.5 },
  { title: "1.75", value: 1.75 },
  { title: "2.00", value: 2.0 },
];
const onSpeedChange = (idx) => {
  currentSpeed.value = speeds[idx];
  if (videoElement.value) {
    videoElement.value.playbackRate = currentSpeed.value.value;
  }
};

// Picture-in-picture (see usePictureInPicture): isPip/pipPanelStyle drive the
// floating panel, videoSize is what all overlays (bbox ellipses, calibration
// markers) read for their own pixel positioning -- it mirrors the shared
// videoStore.videoSize (also read by other cards, e.g. to match their own
// layout to the video) normally, but while in PiP falls back to the
// panel-local pip.contentSize instead, so resizing the floating panel never
// leaks into that shared value. See updateVideoSize below for the other
// half of that: it only writes to the store while docked.
const pip = usePictureInPicture({ onResize: () => updateVideoSize() });
const isPip = pip.isPip;
const lastCardVideoHeight = pip.lastCardContentHeight;
const pipPanelStyle = pip.panelStyle;
const onPipDragStart = pip.onDragStart;
const onPipResizeStart = pip.onResizeStart;
const openPip = () => pip.open(videoFullscreenRoot.value, videoElement.value);
const closePip = pip.close;

const videoSize = computed(() => (isPip.value ? pip.contentSize.value : videoStore.videoSize));

const updateVideoSize = () => {
  nextTick(() => {
    if (!videoElement.value) return;
    const size = pip.measure(videoElement.value);
    if (!isPip.value) {
      videoStore.setVideoSize(size);
    }
  });
};
onMounted(() => {
  updateVideoSize();
  window.addEventListener("resize", updateVideoSize);
});
onBeforeUnmount(() => {
  window.removeEventListener("resize", updateVideoSize);
});
watch(
  () => calibrationAssetStore.isAnyReferenceObjectActive,
  async (newVal) => {
    if (!newVal) {
      await nextTick();
      updateVideoSize();
    }
  }
);

const videoSlider = ref(null);
const videoControl = ref(null);
const maxVideoHeight = ref(0);
const updateMaxHeight = () => {
  if (!videoSlider.value || !videoControl.value) return;
  maxVideoHeight.value =
    (window.innerHeight -
      104 -
      32 -
      videoSlider.value.$el.offsetHeight -
      videoControl.value.$el.offsetHeight -
      60) /
    window.innerHeight;
};
onMounted(() => {
  nextTick(() => updateMaxHeight());
  window.addEventListener("resize", updateMaxHeight);
});
onBeforeUnmount(() => {
  window.removeEventListener("resize", updateMaxHeight);
});
watch(() => window.innerHeight, updateMaxHeight);

const bboxSortedKeys = computed(() =>
  Object.keys(bboxesStore.bboxDataInterpolated)
    .map(Number)
    .sort((a, b) => a - b)
);
const currentFrameKey = computed(() => {
  const keys = bboxSortedKeys.value;
  if (!keys.length) return undefined;
  const target = playerStore.currentTime;
  if (target < keys[0]) return keys[0];
  if (target >= keys[keys.length - 1]) return keys[keys.length - 1];
  // Binary search for largest key <= target
  let lo = 0;
  let hi = keys.length - 1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >>> 1;
    if (keys[mid] <= target) lo = mid;
    else hi = mid - 1;
  }
  return keys[lo];
});

const hovering = ref(false);
const isVideoFullscreen = ref(false);
const videoFullscreenRoot = ref(null);
const toggleVideoFullscreen = () => {
  const root = videoFullscreenRoot.value;

  if (!document.fullscreenElement) {
    root.requestFullscreen?.();
    playerStore.isSynced = false;
  } else {
    document.exitFullscreen?.();
  }
};
const onFullscreenChange = async () => {
  isVideoFullscreen.value = document.fullscreenElement === videoFullscreenRoot.value;

  await nextTick();

  if (videoElement.value) {
    const rect = videoElement.value.getBoundingClientRect();
    const size = { width: rect.width, height: rect.height, top: 0, left: 0 };
    if (isPip.value) {
      pip.contentSize.value = size;
    } else {
      videoStore.setVideoSize(size);
    }
  }
};
// const toggleVideoFullscreen = () => {
//   const div = videoDiv.value;
//   if (!document.fullscreenElement) {
//     div.requestFullscreen?.();
//   } else {
//     document.exitFullscreen?.();
//   }
// };
// const onFullscreenChange = () => {
//   const isVideoFullscreenPrev = isVideoFullscreen.value;
//   isVideoFullscreen.value = document.fullscreenElement === videoDiv.value;

//   if (isVideoFullscreenPrev === true || isVideoFullscreen.value === true) {
//     updateVideoSize();
//   }
// };
onMounted(() => {
  document.addEventListener("fullscreenchange", onFullscreenChange);
});
onBeforeUnmount(() => {
  document.removeEventListener("fullscreenchange", onFullscreenChange);
});

// DEBUG helper: plain rectangular bounding box in pixel space, same x/y/w/h
// indices as getEllipseSvg (position[5..8]).
const getBBoxRectStyle = (position) => {
  const x = position[5];
  const y = position[6];
  const w = position[7];
  const h = position[8];

  const vid = videoSize.value;

  const left = x * vid.width + (isVideoFullscreen.value ? vid.left : 0);
  const top = y * vid.height + (isVideoFullscreen.value ? vid.top : 0);

  return {
    position: "absolute",
    left: left + "px",
    top: top + "px",
    width: w * vid.width + "px",
    height: h * vid.height + "px",
    boxSizing: "border-box",
    border: "2px solid blue",
    pointerEvents: "none",
    zIndex: 11,
  };
};

// Ellipse arc under the player, SoccerNet-style opening (-45°..235°, gap left
// at the top so the player isn't cut through by the line). Geometry is
// entirely intrinsic to the box's own w/h — no position-dependent correction
// term, which is what made the old formula drift for boxes high up in frame.
//
// - rx = full box width (ellipse is 2x as wide as the box), so limbs poking
//   past a tight bounding box still end up inside the ellipse.
// - sideHeight fixes where the ellipse's widest points (left/right) sit,
//   relative to the box's own height.
// - bellyDrop makes the ellipse rounder: the belly radius (ry) is bigger than
//   sideHeight, so the bottom bulges a bit further down past the box's bottom
//   edge, while cy (derived from sideHeight, not ry) keeps the sides fixed.
const getEllipseSvg = (position) => {
  const x = position[5];
  const y = position[6];
  const w = position[7];
  const h = position[8];

  const vid = videoSize.value;

  const color = visualizationStore.getTeamColor(position[1]);

  const boxWidth = w * vid.width;
  const height = h * vid.height;

  const rx = boxWidth;

  const sideHeight = height * 0.05;
  const bellyDrop = height * 0.1;
  const ry = sideHeight + bellyDrop;

  const boxCenterX = (x + w / 2) * vid.width + (isVideoFullscreen.value ? vid.left : 0);
  const top = y * vid.height + (isVideoFullscreen.value ? vid.top : 0);
  const left = boxCenterX - rx;

  const cx = rx;
  const cy = height - sideHeight;

  const startAngle = (-45 * Math.PI) / 180;
  const endAngle = (235 * Math.PI) / 180;

  const sx = cx + rx * Math.cos(startAngle);
  const sy = cy + ry * Math.sin(startAngle);
  const ex = cx + rx * Math.cos(endAngle);
  const ey = cy + ry * Math.sin(endAngle);

  const arcPath = `M ${sx},${sy} A ${rx} ${ry} 0 1 1 ${ex},${ey}`;

  // Player-id label: anchored to the ellipse's actual lowest rendered point
  // (box bottom + bellyDrop), not to the plain box bottom — otherwise a fixed
  // offset from the box edge either overlaps the ellipse on tall boxes (where
  // bellyDrop is large) or leaves an oversized gap on tiny boxes (where
  // bellyDrop is a couple of px). labelGap is then a genuinely constant,
  // absolute pixel distance below the ellipse, regardless of box size.
  const labelGap = 2;
  const labelHeight = 16; // rough rendered height of the 0.8rem number

  const frameBottom = (isVideoFullscreen.value ? vid.top : 0) + vid.height;
  const ellipseBottomAbs = top + height + bellyDrop;
  const fitsBelow = ellipseBottomAbs + labelGap + labelHeight <= frameBottom;

  // Exception: no room below (box sits right at the bottom edge of the
  // frame) — tuck the label above the box instead of letting it run off/get
  // clipped.
  const labelStyle = fitsBelow
    ? { top: `${height + bellyDrop + labelGap}px`, bottom: "auto" }
    : { top: `${-(labelHeight + labelGap)}px`, bottom: "auto" };

  return {
    style: {
      position: "absolute",
      left: left + "px",
      top: top + "px",
      width: rx * 2 + "px",
      height: height + "px",
      overflow: "visible",
      zIndex: 12,
      // Display-only now -- correcting a box moved to AnnotationView, where the frame is
      // shown as a still image large enough to actually drag box edges around.
      cursor: "default",
    },
    viewBox: `0 0 ${rx * 2} ${height}`,
    arc: arcPath,
    color,
    labelStyle,
  };
};

// function tarGzUrlToMp4Url(tarUrl) {
//   const url = new URL(tarUrl);

//   const parts = url.pathname.split("/");
//   const fileName = parts.pop();
//   const mp4Name = fileName.replace(/\.tar\.gz$/, ".mp4");

//   parts.push(mp4Name);
//   url.pathname = parts.join("/");

//   return url.toString();
// }
// watch(
//   () => playerStore.videoUrl,
//   (url) => {
//     if (!url || !videoElement.value) return;
//     const video = videoElement.value;

//     video.src = tarGzUrlToMp4Url(url);
//   }
// );

useHlsVideo(videoElement, { onManifestParsed: () => updateVideoSize() });
</script>

<style scoped>
/* Fixed-height header zone — same pattern and height as TopView.vue's
   matchup-title zone / the tab-window widgets' controls row (see
   TabWindowHeatmap.vue's own .card-header-zone), so that in the default
   video+topview row, both anchor cards' actual content (video / pitch)
   starts at the same y. Keep the height in sync across all of them if you
   ever change it. */
.card-header-zone {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.video-title {
  font-size: 1.25rem;
  font-weight: 500;
  text-align: center;
  margin-top: -28px;
}

.video-control {
  gap: 5px;
}

.video-control > .time-code {
  margin-top: auto;
  margin-bottom: auto;
}

.speed-item {
  cursor: pointer;
}

.speed-item:hover {
  background-color: #f0f0f0;
}

.bounding-box-tooltip ::v-deep(.v-overlay__content) {
  background-color: var(--tooltip-bg);
  border-radius: 2px;
  font-size: 0.7rem;
  line-height: 1.2;
  overflow-wrap: anywhere;
  padding: 5px 10px;
  color: #222;
}

.menu-item {
  cursor: pointer;
}

.menu-item:hover {
  background-color: #f0f0f0;
}

.menu-item .v-list-item-title {
  font-size: 12px;
}

.bounding-box-player-id-old {
  position: absolute;
  left: 50%;
  bottom: -20px;
  transform: translateX(-50%);
  font-size: 0.8rem;
  pointer-events: none;
}

.bounding-box-player-id {
  /* Vertical placement (top/bottom) comes from getEllipseSvg's labelStyle —
     it accounts for the ellipse's bellyDrop and the video frame edge, which a
     static offset here can't. */
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  font-size: 0.8rem;
  pointer-events: none;
}

.video-fullscreen-root {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  height: 100%;
}

.video-wrapper {
  position: relative;
  overflow: hidden;
}

.fullscreen-toggle {
  position: absolute;
  top: 2px;
  right: 2px;
  color: white;
  font-size: 28px;
  opacity: 0;
  transition: opacity 0.3s;
  z-index: 20;
}

.fullscreen-toggle.visible {
  opacity: 0.8;
}

/* .pip-panel / .pip-content / .pip-toggle / .pip-close-button /
   .pip-resize-handle / .pip-placeholder* live in styles/custom.css, shared
   with TopView.vue via the usePictureInPicture composable. */

.fullscreen-controls {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  padding: 16px;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.7), transparent);
  display: flex;
  flex-direction: column;
  gap: 8px;
  opacity: 0;
  transition: opacity 0.3s;
  z-index: 20;
}

.fullscreen-controls.visible {
  opacity: 1;
}

.fullscreen-controls .controls-top {
  display: flex;
  align-items: center;
  gap: 12px;
}

.fullscreen-controls .control-icon {
  color: white;
  font-size: 28px;
  cursor: pointer;
}

.fullscreen-controls .time-code {
  color: white;
  font-size: 0.9rem;
  font-weight: 500;
}

.player-ellipse {
  width: 100%;
  height: 100%;
  overflow: visible;
}

.players-toggle-overlay {
  position: absolute;
  top: 20px;
  left: -15px;
  right: -15px;
  bottom: -10px;
  background: rgb(var(--v-theme-surface));
  border: 2px solid rgba(var(--v-theme-primary), 0.45);
  transition: border-color 0.3s ease;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  z-index: 10;
  overflow: hidden;
}

.players-toggle-close {
  position: absolute;
  top: 2px;
  right: 2px;
  z-index: 11;
}

.players-toggle-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  flex: 1;
  min-height: 0;
  min-width: 0;
  margin: 0 32px 0 16px;
  padding: 12px 0 8px;
  overflow-y: auto;
  overflow-x: hidden;
}

.chart-legend-team {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 5px;
  max-width: 100%;
}

.chart-legend-sep {
  color: #ccc;
  font-size: 18px;
  margin: 0 2px;
  user-select: none;
}

.team-dot {
  height: 20px;
  border-radius: 10px;
  padding: 0 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 0.7rem;
  cursor: pointer;
  border: 2px solid;
  transition: background 0.2s, border 0.2s, color 0.2s;
  user-select: none;
  white-space: nowrap;
}

.team-dot:hover {
  opacity: 0.8;
}

.player-dot {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 0.7rem;
  cursor: pointer;
  border: 2px solid;
  transition: background 0.2s, border 0.2s;
  user-select: none;
}

.entity-kind-bar {
  display: flex;
  gap: 8px;
  width: 100%;
  justify-content: center;
  margin-bottom: 4px;
}

.entity-kind-chip {
  padding: 2px 10px;
  border-radius: 12px;
  border: 1.5px solid rgba(var(--v-theme-primary), 0.6);
  font-size: 0.7rem;
  font-weight: bold;
  cursor: pointer;
  user-select: none;
  color: rgba(var(--v-theme-primary), 1);
  background: transparent;
  transition: background 0.2s, color 0.2s;
}

.entity-kind-chip.active {
  background: rgba(var(--v-theme-primary), 1);
  color: #fff;
}
</style>
