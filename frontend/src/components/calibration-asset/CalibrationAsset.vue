<template>
  <CalibrationAssetMenu v-if="calibrationAssetStore.calibrationAssetObjects.length === 0" />

  <v-container v-else class="d-flex flex-column">
    <v-row justify="center">
      <div ref="topViewFullscreenRoot" class="top-view-fullscreen-root">
        <div
          class="top-view-wrapper"
          data-tour="object-info"
          @mouseenter="hovering = true"
          @mouseleave="hovering = false"
          @click="cancelPendingUnmap"
        >
          <img
            ref="topViewElement"
            class="visualizer-image"
            :src="topViewStore.currentSport.areas.full.image"
            @load="updateTopViewSize"
            :style="
              isTopViewFullscreen
                ? {
                    maxHeight: 100 + 'vh',
                  }
                : {
                    maxHeight: maxVideoHeight * 100 + 'vh',
                    height: videoStore.videoSize.height + 'px',
                  }
            "
          />

          <v-icon
            class="fullscreen-toggle"
            @click="toggleTopViewFullscreen"
            :class="{ visible: hovering }"
          >
            {{ isTopViewFullscreen ? "mdi-fullscreen-exit" : "mdi-fullscreen" }}
          </v-icon>

          <div
            v-if="calibrationAssetStore.isAddingCustomMarker"
            ref="overlayObject"
            @click="calibrationAssetStore.placeCustomMarker"
            @mousemove="onOverlayMouseMove"
            @mouseleave="overlayHoverPos = null"
            :style="{
              position: 'absolute',
              background: 'rgba(255, 255, 255, 0.5)',
              border: '4px solid red',
              cursor: 'crosshair',
              top: '0px',
              left: '0px',
              width: topViewStore.topViewSize.width + 'px',
              height: topViewStore.topViewSize.height + 'px',
            }"
          />

          <svg
            :viewBox="`0 0 ${topViewStore.topViewSize.width} ${topViewStore.topViewSize.height}`"
            style="
              position: absolute;
              top: 0;
              left: 0;
              width: 100%;
              height: 100%;
              pointer-events: none;
            "
          >
            <template v-for="o in calibrationAssetStore.calibrationAssetObjects">
              <circle
                v-if="o.compAreaCoordsRel.length === 1"
                :key="o.id"
                :cx="
                  o.compAreaCoordsRel[0].x *
                    (topViewStore.topViewSize.width *
                      topViewStore.currentSport.areas.full.widthRel) +
                  ((1 - topViewStore.currentSport.areas.full.widthRel) / 2) *
                    topViewStore.topViewSize.width
                "
                :cy="
                  o.compAreaCoordsRel[0].y *
                    (topViewStore.topViewSize.height *
                      topViewStore.currentSport.areas.full.heightRel) +
                  ((1 - topViewStore.currentSport.areas.full.heightRel) / 2) *
                    topViewStore.topViewSize.height
                "
                :disabled="calibrationAssetStore.isAddingCustomMarker"
                :fill="objectColor(o)"
                r="12"
                :fill-opacity="objectOpacity(o)"
                :style="{
                  cursor: 'pointer',
                  pointerEvents: calibrationAssetStore.isAddingCustomMarker ? 'none' : 'all',
                }"
                @click="(event) => calibrationAssetStore.toggleObject(event, o.id)"
                @contextmenu.prevent="onContextMenu(o)"
                class="object-hover-marker"
              />

              <line
                v-if="o.compAreaCoordsRel.length === 2"
                :key="o.id"
                :x1="
                  o.compAreaCoordsRel[0].x *
                    (topViewStore.topViewSize.width *
                      topViewStore.currentSport.areas.full.widthRel) +
                  ((1 - topViewStore.currentSport.areas.full.widthRel) / 2) *
                    topViewStore.topViewSize.width
                "
                :y1="
                  o.compAreaCoordsRel[0].y *
                    (topViewStore.topViewSize.height *
                      topViewStore.currentSport.areas.full.heightRel) +
                  ((1 - topViewStore.currentSport.areas.full.heightRel) / 2) *
                    topViewStore.topViewSize.height
                "
                :x2="
                  o.compAreaCoordsRel[1].x *
                    (topViewStore.topViewSize.width *
                      topViewStore.currentSport.areas.full.widthRel) +
                  ((1 - topViewStore.currentSport.areas.full.widthRel) / 2) *
                    topViewStore.topViewSize.width
                "
                :y2="
                  o.compAreaCoordsRel[1].y *
                    (topViewStore.topViewSize.height *
                      topViewStore.currentSport.areas.full.heightRel) +
                  ((1 - topViewStore.currentSport.areas.full.heightRel) / 2) *
                    topViewStore.topViewSize.height
                "
                :disabled="calibrationAssetStore.isAddingCustomMarker"
                :stroke="objectColor(o)"
                stroke-width="12"
                :stroke-opacity="objectOpacity(o)"
                :style="{
                  cursor: 'pointer',
                  pointerEvents: calibrationAssetStore.isAddingCustomMarker ? 'none' : 'all',
                }"
                @click="(event) => calibrationAssetStore.toggleObject(event, o.id)"
                class="object-hover-segment"
              />

              <path
                v-if="o.compAreaCoordsRel.length > 2"
                :key="o.id"
                :d="
                  (() => {
                    const toScreen = (p) => ({
                      x:
                        p.x *
                          (topViewStore.topViewSize.width *
                            topViewStore.currentSport.areas.full.widthRel) +
                        ((1 - topViewStore.currentSport.areas.full.widthRel) / 2) *
                          topViewStore.topViewSize.width,
                      y:
                        p.y *
                          (topViewStore.topViewSize.height *
                            topViewStore.currentSport.areas.full.heightRel) +
                        ((1 - topViewStore.currentSport.areas.full.heightRel) / 2) *
                          topViewStore.topViewSize.height,
                    });

                    const points = o.compAreaCoordsRel.map(toScreen);

                    let d = `M ${points[0].x} ${points[0].y}`;

                    for (let i = 0; i < points.length - 1; i++) {
                      const p0 = points[i === 0 ? 0 : i - 1];
                      const p1 = points[i];
                      const p2 = points[i + 1];
                      const p3 = points[i + 2 < points.length ? i + 2 : points.length - 1];

                      const c1x = p1.x + (p2.x - p0.x) / 6;
                      const c1y = p1.y + (p2.y - p0.y) / 6;
                      const c2x = p2.x - (p3.x - p1.x) / 6;
                      const c2y = p2.y - (p3.y - p1.y) / 6;

                      d += ` C ${c1x} ${c1y}, ${c2x} ${c2y}, ${p2.x} ${p2.y}`;
                    }

                    return d;
                  })()
                "
                :stroke="objectColor(o)"
                stroke-width="12"
                :stroke-opacity="objectOpacity(o)"
                fill="none"
                :style="{
                  cursor: 'pointer',
                  pointerEvents: calibrationAssetStore.isAddingCustomMarker ? 'none' : 'all',
                }"
                @click="(event) => calibrationAssetStore.toggleObject(event, o.id)"
                class="object-hover-segment"
              />
            </template>
          </svg>
          <svg
            :viewBox="`0 0 ${topViewStore.topViewSize.width} ${topViewStore.topViewSize.height}`"
            style="
              position: absolute;
              top: 0;
              left: 0;
              width: 100%;
              height: 100%;
              pointer-events: none;
            "
          >
            <template v-for="o in calibrationAssetStore.calibrationAssetObjects">
              <template v-if="o.name?.startsWith('Custom-object')">
                <circle
                  v-if="o.compAreaCoordsRel.length === 1"
                  v-show="showDeleteButton"
                  :key="'delete-' + o.id"
                  :cx="
                    o.compAreaCoordsRel[0].x *
                      (topViewStore.topViewSize.width *
                        topViewStore.currentSport.areas.full.widthRel) +
                    ((1 - topViewStore.currentSport.areas.full.widthRel) / 2) *
                      topViewStore.topViewSize.width
                  "
                  :cy="
                    o.compAreaCoordsRel[0].y *
                      (topViewStore.topViewSize.height *
                        topViewStore.currentSport.areas.full.heightRel) +
                    ((1 - topViewStore.currentSport.areas.full.heightRel) / 2) *
                      topViewStore.topViewSize.height
                  "
                  r="12"
                  fill="none"
                  style="cursor: pointer; pointer-events: all"
                  @click="calibrationAssetStore.deleteCustomMarker(o.id)"
                  class="delete-marker-position"
                />
                <text
                  v-if="o.compAreaCoordsRel.length === 1"
                  v-show="showDeleteButton"
                  :x="
                    o.compAreaCoordsRel[0].x *
                      (topViewStore.topViewSize.width *
                        topViewStore.currentSport.areas.full.widthRel) +
                    ((1 - topViewStore.currentSport.areas.full.widthRel) / 2) *
                      topViewStore.topViewSize.width
                  "
                  :y="
                    o.compAreaCoordsRel[0].y *
                      (topViewStore.topViewSize.height *
                        topViewStore.currentSport.areas.full.heightRel) +
                    ((1 - topViewStore.currentSport.areas.full.heightRel) / 2) *
                      topViewStore.topViewSize.height +
                    6
                  "
                  text-anchor="middle"
                  font-size="16"
                  fill="red"
                >
                  ✕
                </text>

                <line
                  v-if="o.compAreaCoordsRel.length === 2"
                  v-show="showDeleteButton"
                  :key="'delete-' + o.id"
                  :x1="
                    o.compAreaCoordsRel[0].x *
                      (topViewStore.topViewSize.width *
                        topViewStore.currentSport.areas.full.widthRel) +
                    ((1 - topViewStore.currentSport.areas.full.widthRel) / 2) *
                      topViewStore.topViewSize.width
                  "
                  :y1="
                    o.compAreaCoordsRel[0].y *
                      (topViewStore.topViewSize.height *
                        topViewStore.currentSport.areas.full.heightRel) +
                    ((1 - topViewStore.currentSport.areas.full.heightRel) / 2) *
                      topViewStore.topViewSize.height
                  "
                  :x2="
                    o.compAreaCoordsRel[1].x *
                      (topViewStore.topViewSize.width *
                        topViewStore.currentSport.areas.full.widthRel) +
                    ((1 - topViewStore.currentSport.areas.full.widthRel) / 2) *
                      topViewStore.topViewSize.width
                  "
                  :y2="
                    o.compAreaCoordsRel[1].y *
                      (topViewStore.topViewSize.height *
                        topViewStore.currentSport.areas.full.heightRel) +
                    ((1 - topViewStore.currentSport.areas.full.heightRel) / 2) *
                      topViewStore.topViewSize.height
                  "
                  stroke-width="12"
                  fill="none"
                  style="cursor: pointer; pointer-events: all"
                  @click="calibrationAssetStore.deleteCustomMarker(o.id)"
                  class="delete-segment-position"
                />
                <text
                  v-if="o.compAreaCoordsRel.length === 2"
                  v-show="showDeleteButton"
                  :x="
                    (o.compAreaCoordsRel[0].x *
                      (topViewStore.topViewSize.width *
                        topViewStore.currentSport.areas.full.widthRel) +
                      ((1 - topViewStore.currentSport.areas.full.widthRel) / 2) *
                        topViewStore.topViewSize.width +
                      o.compAreaCoordsRel[1].x *
                        (topViewStore.topViewSize.width *
                          topViewStore.currentSport.areas.full.widthRel) +
                      ((1 - topViewStore.currentSport.areas.full.widthRel) / 2) *
                        topViewStore.topViewSize.width) /
                    2
                  "
                  :y="
                    (o.compAreaCoordsRel[0].y *
                      (topViewStore.topViewSize.height *
                        topViewStore.currentSport.areas.full.heightRel) +
                      ((1 - topViewStore.currentSport.areas.full.heightRel) / 2) *
                        topViewStore.topViewSize.height +
                      o.compAreaCoordsRel[1].y *
                        (topViewStore.topViewSize.height *
                          topViewStore.currentSport.areas.full.heightRel) +
                      ((1 - topViewStore.currentSport.areas.full.heightRel) / 2) *
                        topViewStore.topViewSize.height) /
                      2 +
                    5
                  "
                  text-anchor="middle"
                  font-size="16"
                  fill="red"
                >
                  ✕
                </text>

                <path
                  v-if="o.compAreaCoordsRel.length > 2"
                  v-show="showDeleteButton"
                  :key="'delete-' + o.id"
                  :d="
                    (() => {
                      const toScreen = (p) => ({
                        x:
                          p.x *
                            (topViewStore.topViewSize.width *
                              topViewStore.currentSport.areas.full.widthRel) +
                          ((1 - topViewStore.currentSport.areas.full.widthRel) / 2) *
                            topViewStore.topViewSize.width,
                        y:
                          p.y *
                            (topViewStore.topViewSize.height *
                              topViewStore.currentSport.areas.full.heightRel) +
                          ((1 - topViewStore.currentSport.areas.full.heightRel) / 2) *
                            topViewStore.topViewSize.height,
                      });

                      const points = o.compAreaCoordsRel.map(toScreen);

                      let d = `M ${points[0].x} ${points[0].y}`;

                      for (let i = 0; i < points.length - 1; i++) {
                        const p0 = points[i === 0 ? 0 : i - 1];
                        const p1 = points[i];
                        const p2 = points[i + 1];
                        const p3 = points[i + 2 < points.length ? i + 2 : points.length - 1];

                        const c1x = p1.x + (p2.x - p0.x) / 6;
                        const c1y = p1.y + (p2.y - p0.y) / 6;
                        const c2x = p2.x - (p3.x - p1.x) / 6;
                        const c2y = p2.y - (p3.y - p1.y) / 6;

                        d += ` C ${c1x} ${c1y}, ${c2x} ${c2y}, ${p2.x} ${p2.y}`;
                      }

                      return d;
                    })()
                  "
                  stroke-width="12"
                  fill="none"
                  style="cursor: pointer; pointer-events: all"
                  @click="calibrationAssetStore.deleteCustomMarker(o.id)"
                  class="delete-segment-position"
                />
                <text
                  v-if="o.compAreaCoordsRel.length > 2"
                  v-show="showDeleteButton"
                  :x="
                    (isTopViewFullscreen ? topViewStore.topViewSize.left : 0) +
                    o.compAreaCoordsRel[2].x *
                      (topViewStore.topViewSize.width *
                        topViewStore.currentSport.areas.full.widthRel) +
                    ((1 - topViewStore.currentSport.areas.full.widthRel) / 2) *
                      topViewStore.topViewSize.width
                  "
                  :y="
                    (isTopViewFullscreen ? topViewStore.topViewSize.top : 0) +
                    o.compAreaCoordsRel[2].y *
                      (topViewStore.topViewSize.height *
                        topViewStore.currentSport.areas.full.heightRel) +
                    ((1 - topViewStore.currentSport.areas.full.heightRel) / 2) *
                      topViewStore.topViewSize.height +
                    6
                  "
                  text-anchor="middle"
                  font-size="16"
                  fill="red"
                >
                  ✕
                </text>
              </template>
            </template>
          </svg>

          <template v-if="pendingUnmapId !== null">
            <template v-for="o in calibrationAssetStore.calibrationAssetObjects">
              <div
                v-if="o.id === pendingUnmapId"
                :key="'unmap-' + o.id"
                :style="{
                  position: 'absolute',
                  left: unmapIconPos(o).x + 'px',
                  top: unmapIconPos(o).y + 'px',
                  transform: 'translate(-50%, -50%)',
                  width: '30px',
                  height: '30px',
                  borderRadius: '50%',
                  backgroundColor: calibrationAssetStore.objectColorMap[o.id] ?? '#888888',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'pointer',
                  pointerEvents: 'all',
                  zIndex: 10,
                }"
                @click.stop="confirmUnmap"
              >
                <v-icon color="white" size="18">mdi-sync-off</v-icon>
              </div>
            </template>
          </template>

          <!-- <div
          v-for="point in calibrationAssetStore.topViewObjectProjection"
          v-show="calibrationAssetStore.showVideoAsset"
          :key="point"
          :style="{
            position: 'absolute',
            width: '5px',
            height: '5px',
            backgroundColor: 'blue',
            borderRadius: '50%',
            transform: 'translate(-50%, -50%)',
            top: isTopViewFullscreen
              ? topViewStore.topViewSize.top +
                point.y * (topViewStore.topViewSize.height * topViewStore.currentSport.heightRel) +
                ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height +
                'px'
              : point.y * (topViewStore.topViewSize.height * topViewStore.currentSport.heightRel) +
                ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height +
                'px',
            left: isTopViewFullscreen
              ? topViewStore.topViewSize.left +
                point.x * (topViewStore.topViewSize.width * topViewStore.currentSport.widthRel) +
                ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width +
                'px'
              : point.x * (topViewStore.topViewSize.width * topViewStore.currentSport.widthRel) +
                ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width +
                'px',
            pointerEvents: 'none',
          }"
        /> -->
          <svg
            :viewBox="`0 0 ${topViewStore.topViewSize.width} ${topViewStore.topViewSize.height}`"
            style="
              position: absolute;
              top: 0;
              left: 0;
              width: 100%;
              height: 100%;
              pointer-events: none;
            "
          >
            <template v-for="o in calibrationAssetStore.topViewObjectProjection">
              <circle
                v-if="o.length === 1"
                v-show="calibrationAssetStore.showVideoAsset"
                :key="o.id"
                :cx="
                  o[0].x *
                    (topViewStore.topViewSize.width *
                      topViewStore.currentSport.areas.full.widthRel) +
                  ((1 - topViewStore.currentSport.areas.full.widthRel) / 2) *
                    topViewStore.topViewSize.width
                "
                :cy="
                  o[0].y *
                    (topViewStore.topViewSize.height *
                      topViewStore.currentSport.areas.full.heightRel) +
                  ((1 - topViewStore.currentSport.areas.full.heightRel) / 2) *
                    topViewStore.topViewSize.height
                "
                fill="blue"
                r="5"
                style="pointer-events: none"
              />

              <line
                v-if="o.length === 2"
                v-show="calibrationAssetStore.showVideoAsset"
                :key="o.id"
                :x1="
                  o[0].x *
                    (topViewStore.topViewSize.width *
                      topViewStore.currentSport.areas.full.widthRel) +
                  ((1 - topViewStore.currentSport.areas.full.widthRel) / 2) *
                    topViewStore.topViewSize.width
                "
                :y1="
                  o[0].y *
                    (topViewStore.topViewSize.height *
                      topViewStore.currentSport.areas.full.heightRel) +
                  ((1 - topViewStore.currentSport.areas.full.heightRel) / 2) *
                    topViewStore.topViewSize.height
                "
                :x2="
                  o[1].x *
                    (topViewStore.topViewSize.width *
                      topViewStore.currentSport.areas.full.widthRel) +
                  ((1 - topViewStore.currentSport.areas.full.widthRel) / 2) *
                    topViewStore.topViewSize.width
                "
                :y2="
                  o[1].y *
                    (topViewStore.topViewSize.height *
                      topViewStore.currentSport.areas.full.heightRel) +
                  ((1 - topViewStore.currentSport.areas.full.heightRel) / 2) *
                    topViewStore.topViewSize.height
                "
                stroke="blue"
                stroke-width="5"
                style="pointer-events: none"
              />

              <path
                v-if="o.length > 2"
                v-show="calibrationAssetStore.showVideoAsset"
                :key="o.id"
                :d="
                  (() => {
                    const toScreen = (p) => ({
                      x:
                        p.x *
                          (topViewStore.topViewSize.width *
                            topViewStore.currentSport.areas.full.widthRel) +
                        ((1 - topViewStore.currentSport.areas.full.widthRel) / 2) *
                          topViewStore.topViewSize.width,
                      y:
                        p.y *
                          (topViewStore.topViewSize.height *
                            topViewStore.currentSport.areas.full.heightRel) +
                        ((1 - topViewStore.currentSport.areas.full.heightRel) / 2) *
                          topViewStore.topViewSize.height,
                    });

                    const points = o.map(toScreen);

                    let d = `M ${points[0].x} ${points[0].y}`;

                    for (let i = 0; i < points.length - 1; i++) {
                      const p0 = points[i === 0 ? 0 : i - 1];
                      const p1 = points[i];
                      const p2 = points[i + 1];
                      const p3 = points[i + 2 < points.length ? i + 2 : points.length - 1];

                      const c1x = p1.x + (p2.x - p0.x) / 6;
                      const c1y = p1.y + (p2.y - p0.y) / 6;
                      const c2x = p2.x - (p3.x - p1.x) / 6;
                      const c2y = p2.y - (p3.y - p1.y) / 6;

                      d += ` C ${c1x} ${c1y}, ${c2x} ${c2y}, ${p2.x} ${p2.y}`;
                    }

                    return d;
                  })()
                "
                stroke="blue"
                stroke-width="5"
                fill="none"
                style="pointer-events: none"
              />
            </template>
          </svg>
        </div>
      </div>
    </v-row>

    <v-row
      ref="videoControl"
      class="video-control mt-6 mb-n2 justify-center align-center"
      style="height: 60px; position: relative"
      data-tour="calibration-asset-edit-row"
    >
      <v-menu location="top center">
        <template #activator="{ props }">
          <v-btn v-bind="props" size="small" data-tour="calibration-asset-btn">
            {{ $t("calibration_asset.title") }}
          </v-btn>
        </template>

        <v-list class="py-0" density="compact">
          <v-list-item class="menu-item" @click="showModalCalibrationAssetCreate = true">
            <v-list-item-title>
              {{ $t("calibration_asset.create") }}
            </v-list-item-title>
          </v-list-item>

          <v-list-item
            class="menu-item"
            v-if="!calibrationAssetStore.calibrationAssetId"
            @click="showModalCalibrationAssetSave = true"
          >
            <v-list-item-title>
              {{ $t("calibration_asset.save") }}
            </v-list-item-title>
          </v-list-item>

          <v-list-item
            class="menu-item"
            v-if="calibrationAssetStore.calibrationAssetId"
            @click="showModalCalibrationAssetUpdate = true"
          >
            <v-list-item-title>
              {{ $t("calibration_asset.update") }}
            </v-list-item-title>
          </v-list-item>
          <v-list-item class="menu-item" @click="showModalCalibrationAssetSelect = true">
            <v-list-item-title>
              {{ $t("calibration_asset.select") }}
            </v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>
      <ModalCalibrationAssetCreate
        v-if="showModalCalibrationAssetCreate"
        v-model="showModalCalibrationAssetCreate"
      />
      <ModalCalibrationAssetSave
        v-if="showModalCalibrationAssetSave"
        v-model="showModalCalibrationAssetSave"
      />
      <ModalCalibrationAssetSelect
        v-if="showModalCalibrationAssetSelect"
        v-model="showModalCalibrationAssetSelect"
      />
      <ModalCalibrationAssetUpdate
        v-if="showModalCalibrationAssetUpdate"
        v-model="showModalCalibrationAssetUpdate"
      />

      <v-menu v-model="showMarkerTypeMenu" location="top" :close-on-content-click="false">
        <template #activator="{ props }">
          <v-btn v-bind="props" size="small" data-tour="calibration-object-btn">
            {{
              calibrationAssetStore.calibrationAssetType === "marker"
                ? $t("calibration_asset.marker.title")
                : $t("calibration_asset.segments.title")
            }}
          </v-btn>
        </template>
        <v-list class="py-0" density="compact" width="200px">
          <v-list-item
            class="menu-item"
            @click="
              () => {
                calibrationAssetStore.toggleVideoAsset();
                showMarkerTypeMenu = false;
              }
            "
          >
            <v-list-item-title class="d-flex justify-space-between">
              {{
                calibrationAssetStore.calibrationAssetType === "marker"
                  ? $t("calibration_asset.marker.view_vid_marker")
                  : $t("calibration_asset.segments.view_vid_segments")
              }}
              <v-icon
                :class="{
                  'text-disabled': !calibrationAssetStore.showVideoAsset,
                  'text-red': calibrationAssetStore.showVideoAsset,
                }"
                class="mb-1"
                size="small"
              >
                mdi-check
              </v-icon>
            </v-list-item-title>
          </v-list-item>

          <v-list-item
            v-if="calibrationAssetStore.calibrationAssetType === 'marker'"
            class="menu-item"
            @click="
              () => {
                addCustomMarker();
                showMarkerTypeMenu = false;
              }
            "
          >
            <v-list-item-title>
              {{ $t("calibration_asset.marker.add_custom_marker") }}
            </v-list-item-title>
          </v-list-item>

          <v-list-item
            v-if="calibrationAssetStore.calibrationAssetType === 'marker'"
            class="menu-item"
            @click="
              () => {
                showDeleteButton = !showDeleteButton;
                showMarkerTypeMenu = false;
              }
            "
          >
            <v-list-item-title>
              {{ $t("calibration_asset.marker.delete_custom_marker") }}
            </v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>

      <v-menu
        v-if="
          calibrationAssetStore.timeChangeConflict &&
          calibrationAssetStore.videoObjectTime !== playerStore.currentTime
        "
        open-on-hover
        :close-delay="200"
        location="top"
      >
        <template #activator="{ props }">
          <v-icon v-bind="props" color="warning" size="small" class="ml-2 mt-1"
            >mdi-information-outline</v-icon
          >
        </template>
        <div class="time-conflict-menu pa-3 d-flex flex-column align-center">
          <div>
            {{
              $t("calibration_asset.time-conflict", {
                time: getTimecode(calibrationAssetStore.videoObjectTime ?? 0),
              })
            }}
          </div>
          <v-btn variant="outlined" size="small" class="mt-2" @click="goToMarkerTime">
            {{
              $t("calibration_asset.go_to_marker_time", {
                time: getTimecode(calibrationAssetStore.videoObjectTime ?? 0),
              })
            }}
          </v-btn>
        </div>
      </v-menu>

      <div v-if="calibrationAssetStore.isAddingCustomMarker" class="custom-marker-coords-overlay">
        <div class="text-caption coords-live">
          X:&nbsp;<template v-if="overlayHoverPos"
            ><span class="coords-val">{{ overlayHoverPos.x }}</span
            >&nbsp;m</template
          ><template v-else>–</template> &nbsp;&nbsp;&nbsp; Y:&nbsp;<template v-if="overlayHoverPos"
            ><span class="coords-val">{{ overlayHoverPos.y }}</span
            >&nbsp;m</template
          ><template v-else>–</template>
        </div>

        <v-text-field
          v-model.number="manualX"
          label="X (m)"
          type="number"
          step="0.1"
          density="compact"
          variant="outlined"
          hide-details
          class="coords-input ml-4"
        />
        <v-text-field
          v-model.number="manualY"
          label="Y (m)"
          type="number"
          step="0.1"
          density="compact"
          variant="outlined"
          hide-details
          class="coords-input"
        />
        <v-btn
          size="small"
          :disabled="manualX === null || manualY === null"
          @click="confirmManualInput"
        >
          {{ $t("button.add") }}
        </v-btn>
      </div>
    </v-row>
  </v-container>

  <v-snackbar color="accent" v-model="showvideoObjectActionSnackbar">
    <div class="d-flex flex-column align-center">
      <div class="d-flex justify-center">
        <snackbar-icon-warning />
        <span class="text-h6">{{ videoObjectActionMessage }}</span>
      </div>
      <v-btn variant="outlined" class="mt-2" @click="goToMarkerTime">
        {{
          $t("calibration_asset.go_to_marker_time", {
            time: getTimecode(calibrationAssetStore.videoObjectTime ?? 0),
          })
        }}
      </v-btn>
    </div>
  </v-snackbar>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from "vue";
import { useI18n } from "vue-i18n";
import { getTimecode } from "@/plugins/time";
import { useTopViewStore } from "@/stores/top_view";
import { useCalibrationAssetStore } from "@/stores/calibration_asset";
import { useVideoStore } from "@/stores/video";
import { usePlayerStore } from "@/stores/player";
import CalibrationAssetMenu from "@/components/calibration-asset/CalibrationAssetMenu.vue";
import ModalCalibrationAssetCreate from "@/components/calibration-asset/ModalCalibrationAssetCreate.vue";
import ModalCalibrationAssetSave from "@/components/calibration-asset/ModalCalibrationAssetSave.vue";
import ModalCalibrationAssetSelect from "@/components/calibration-asset/ModalCalibrationAssetSelect.vue";
import ModalCalibrationAssetUpdate from "@/components/calibration-asset/ModalCalibrationAssetUpdate.vue";

const { t } = useI18n();

const topViewStore = useTopViewStore();
const calibrationAssetStore = useCalibrationAssetStore();
const videoStore = useVideoStore();
const playerStore = usePlayerStore();

const props = defineProps({
  showItems: {
    type: Boolean,
    default: false,
  },
});

const topViewElement = ref(null);
const updateTopViewSize = async () => {
  await nextTick();
  await waitForStableElement(topViewElement);

  if (topViewElement.value) {
    const rect = topViewElement.value.getBoundingClientRect();
    topViewStore.setTopViewSize({
      width: rect.width,
      height: rect.height,
      top: rect.top,
      left: rect.left,
    });
  }
};
function waitForStableElement(elRef) {
  return new Promise((resolve) => {
    let lastRect = null;
    let stableCounter = 0;

    const check = () => {
      const el = elRef.value;
      if (!el) {
        requestAnimationFrame(check);
        return;
      }

      const rect = el.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0 || rect.top === 0 || rect.left === 0) {
        requestAnimationFrame(check);
        return;
      }

      if (
        lastRect &&
        rect.top === lastRect.top &&
        rect.left === lastRect.left &&
        rect.width === lastRect.width &&
        rect.height === lastRect.height
      ) {
        stableCounter++;
      } else {
        stableCounter = 0;
      }

      lastRect = rect;

      if (stableCounter >= 3) {
        resolve();
      } else {
        requestAnimationFrame(check);
      }
    };

    check();
  });
}
const resizeObserver = new ResizeObserver(() => {
  updateTopViewSize();
});
onMounted(() => {
  window.addEventListener("resize", updateTopViewSize);
  if (topViewElement.value) {
    resizeObserver.observe(topViewElement.value);
    updateTopViewSize();
  }
});
onBeforeUnmount(() => {
  window.removeEventListener("resize", updateTopViewSize);
  if (topViewElement.value) {
    resizeObserver.unobserve(topViewElement.value);
  }
});

const showModalCalibrationAssetCreate = ref(false);
const showModalCalibrationAssetSave = ref(false);
const showModalCalibrationAssetSelect = ref(false);
const showModalCalibrationAssetUpdate = ref(false);

const toSvgX = (relX) =>
  relX * (topViewStore.topViewSize.width * topViewStore.currentSport.areas.full.widthRel) +
  ((1 - topViewStore.currentSport.areas.full.widthRel) / 2) * topViewStore.topViewSize.width;
const toSvgY = (relY) =>
  relY * (topViewStore.topViewSize.height * topViewStore.currentSport.areas.full.heightRel) +
  ((1 - topViewStore.currentSport.areas.full.heightRel) / 2) * topViewStore.topViewSize.height;

const fieldLength = computed(() => playerStore.video?.field_length ?? 105);
const fieldWidth = computed(() => playerStore.video?.field_width ?? 68);

const relToMeters = (relX, relY) => ({
  x: (relX * fieldLength.value).toFixed(1),
  y: ((1 - relY) * fieldWidth.value).toFixed(1),
});

const overlayHoverPos = ref(null);
const onOverlayMouseMove = (event) => {
  const ts = topViewStore.topViewSize;
  const sp = topViewStore.currentSport;
  const relX =
    (event.clientX - (ts.left + ((1 - sp.widthRel) / 2) * ts.width)) / (ts.width * sp.widthRel);
  const relY =
    (event.clientY - (ts.top + ((1 - sp.heightRel) / 2) * ts.height)) / (ts.height * sp.heightRel);
  overlayHoverPos.value = relToMeters(relX, relY);
};

const manualX = ref(null);
const manualY = ref(null);
const confirmManualInput = () => {
  if (manualX.value === null || manualY.value === null) return;
  const relX = manualX.value / fieldLength.value;
  const relY = 1 - manualY.value / fieldWidth.value;
  calibrationAssetStore.placeCustomMarkerByCoords(relX, relY);
  manualX.value = null;
  manualY.value = null;
  overlayHoverPos.value = null;
};

const isMapped = (obj) => obj.videoCoordsRel.some((p) => p.x !== null && p.y !== null);

const unmapIconPos = (obj) => {
  const c = obj.compAreaCoordsRel;
  if (c.length === 1) return { x: toSvgX(c[0].x), y: toSvgY(c[0].y) };
  if (c.length === 2)
    return { x: (toSvgX(c[0].x) + toSvgX(c[1].x)) / 2, y: (toSvgY(c[0].y) + toSvgY(c[1].y)) / 2 };
  const mid = Math.floor(c.length / 2);
  return { x: toSvgX(c[mid].x), y: toSvgY(c[mid].y) };
};

const pendingUnmapId = ref(null);
const onContextMenu = (obj) => {
  if (isMapped(obj)) {
    pendingUnmapId.value = obj.id;
  }
};
const confirmUnmap = () => {
  if (pendingUnmapId.value !== null) {
    calibrationAssetStore.unmapObject(pendingUnmapId.value);
    pendingUnmapId.value = null;
  }
};
const cancelPendingUnmap = () => {
  pendingUnmapId.value = null;
};
const objectColor = (obj) => {
  if (obj.active || calibrationAssetStore.hoveredVideoObject === obj.id) return "white";
  if (isMapped(obj)) return calibrationAssetStore.objectColorMap[obj.id] ?? "#888888";
  return "#999999";
};
const objectOpacity = (obj) => {
  if (obj.active || calibrationAssetStore.hoveredVideoObject === obj.id) return 1;
  if (isMapped(obj)) return 0.9;
  return 0.45;
};

const showDeleteButton = ref(false);
const showMarkerTypeMenu = ref(false);
const addCustomMarker = () => {
  if (showDeleteButton.value) {
    showDeleteButton.value = false;
  }
  nextTick(() => {
    calibrationAssetStore.addCustomMarker();
  });
};

const overlayObject = ref(null);

const maxVideoHeight = ref(0);
const videoControl = ref(null);
const updateMaxHeight = () => {
  if (!videoControl.value) return;
  maxVideoHeight.value =
    (window.innerHeight - 104 - 32 - videoControl.value.$el.offsetHeight - 60) / window.innerHeight;
};
onMounted(() => {
  nextTick(() => updateMaxHeight());
  window.addEventListener("resize", updateMaxHeight);
});
watch(() => window.innerHeight, updateMaxHeight);
watch(videoControl, (newVal) => {
  if (newVal) {
    nextTick(() => updateMaxHeight());
  }
});

const hovering = ref(false);
const isTopViewFullscreen = ref(false);
const topViewFullscreenRoot = ref(null);
const toggleTopViewFullscreen = () => {
  const root = topViewFullscreenRoot.value;

  if (!document.fullscreenElement) {
    root.requestFullscreen?.();
    playerStore.isSynced = false;
  } else {
    document.exitFullscreen?.();
  }
};
const onFullscreenChange = async () => {
  isTopViewFullscreen.value = document.fullscreenElement === topViewFullscreenRoot.value;

  await nextTick();

  if (topViewElement.value) {
    const rect = topViewElement.value.getBoundingClientRect();
    topViewStore.setTopViewSize({
      width: rect.width,
      height: rect.height,
      top: 0,
      left: 0,
    });
  }
};
onMounted(() => {
  document.addEventListener("fullscreenchange", onFullscreenChange);
});
onBeforeUnmount(() => {
  document.removeEventListener("fullscreenchange", onFullscreenChange);
});

watch(
  () => playerStore.currentTime,
  (newTime, oldTime) => {
    if (
      oldTime === undefined ||
      newTime === oldTime ||
      calibrationAssetStore.timeChangeConflict ||
      !calibrationAssetStore.isAssetEdited
    )
      return;

    const hasVideoCoords = calibrationAssetStore.calibrationAssetObjects.some((o) => {
      const v = o.videoCoordsRel;
      return v && (v.x !== null || v.y !== null);
    });

    if (hasVideoCoords) {
      calibrationAssetStore.timeChangeConflict = true;
      showvideoObjectActionSnackbar.value = true;
      calibrationAssetStore.videoObjectTime = oldTime;
    }
  }
);

const showvideoObjectActionSnackbar = ref(false);
const videoObjectActionMessage = ref("");
const goToMarkerTime = () => {
  if (calibrationAssetStore.videoObjectTime !== null) {
    playerStore.setCurrentTime(calibrationAssetStore.videoObjectTime);
    if (showvideoObjectActionSnackbar.value) {
      showvideoObjectActionSnackbar.value = false;
    }
  }
};
const resetVideoObjectActionSnackbar = async () => {
  showvideoObjectActionSnackbar.value = false;
  await nextTick();
  showvideoObjectActionSnackbar.value = true;
};
watch([() => calibrationAssetStore.timeChangeConflict], ([warning]) => {
  if (warning === true) {
    videoObjectActionMessage.value = t("modal.calibration_asset.video_marker.warning", {
      time: getTimecode(calibrationAssetStore.videoObjectTime ?? 0),
    });
    resetVideoObjectActionSnackbar();
  }
});
</script>

<style scoped>
.visualizer-image {
  display: block;
  max-width: 100%;
  max-height: 100%;
}

.delete-marker-position:hover {
  fill: red;
  fill-opacity: 0.2;
}

.delete-segment-position:hover {
  stroke: red;
  stroke-opacity: 0.2;
}

.video-control {
  gap: 5px;
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

.top-view-fullscreen-root {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  height: 100%;
}

.top-view-wrapper {
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

.fullscreen-controls {
  position: absolute;
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

.time-conflict-menu {
  background-color: rgb(var(--v-theme-accent));
  color: white;
  border-radius: 4px;
  /* font-size: 12px; */
  width: 500px;
}

::v-deep(.object-hover-marker):hover {
  fill: darkgray;
  stroke-width: 13;
}

::v-deep(.object-hover-segment):hover {
  stroke: darkgray;
  stroke-width: 13;
}

.custom-marker-coords-overlay {
  position: absolute;
  top: 0px;
  left: 0px;
  right: 0px;
  bottom: 0px;
  background: white;
  border: 2px solid rgba(var(--v-theme-primary), 0.45);
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  z-index: 10;
  padding: 0 12px;
}

.coords-live {
  white-space: nowrap;
  font-size: 14px;
  font-variant-numeric: tabular-nums;
}

.coords-val {
  display: inline-block;
  min-width: 4.5ch;
  text-align: right;
}

.coords-input {
  flex: 0 0 72px;
  width: 72px;
}

.coords-input :deep(.v-field__input) {
  padding-top: 0;
  padding-bottom: 0;
  min-height: 28px;
  font-size: 12px;
}

.coords-input :deep(.v-label) {
  font-size: 12px;
}

.coords-input :deep(input[type="number"]::-webkit-inner-spin-button),
.coords-input :deep(input[type="number"]::-webkit-outer-spin-button) {
  -webkit-appearance: none;
  margin: 0;
}

.coords-input :deep(input[type="number"]) {
  -moz-appearance: textfield;
}
</style>
