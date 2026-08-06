<template>
  <div v-if="!hasPositionData && posdataWorkerStore.isLoading" class="kpi-loading-card">
    <div class="kpi-spinner"><i class="mdi mdi-loading mdi-spin" /></div>
    <div class="kpi-loading-text">
      {{
        posdataWorkerStore.loadProgress > 0 && posdataWorkerStore.loadProgress < 100
          ? `${posdataWorkerStore.loadProgress}%`
          : ""
      }}
    </div>
  </div>

  <v-row
    v-else-if="!hasPositionData"
    class="text-h6 text-grey font-weight-light mx-16 px-10"
    style="
      align-items: center;
      justify-content: center;
      text-align: center;
      line-height: 1.5;
      height: 25vh;
    "
    v-html="kpiPosdataNotSelectedText"
  />

  <div v-else-if="!hasKpiData && visualizationStore.isLoadingKpi" class="kpi-loading-card">
    <div class="kpi-spinner"><i class="mdi mdi-loading mdi-spin" /></div>
  </div>

  <v-row
    v-else-if="!hasKpiData"
    class="text-h6 text-grey font-weight-light mx-16 px-10"
    style="
      align-items: center;
      justify-content: center;
      text-align: center;
      line-height: 1.5;
      height: 25vh;
    "
    v-html="kpiNotSelectedText"
  />

  <div v-else class="d-flex flex-column flex-nowrap pa-4" :class="{ 'kpi-fill-height': dense }">
    <div class="card-header-zone">
      <v-row
        align="center"
        class="flex-nowrap mx-n4 mt-n8"
        style="width: 100%"
        data-tour="kpi-controls-row"
      >
        <v-col
          cols="auto"
          class="d-flex align-center flex-shrink-0"
          style="gap: 12px"
          data-tour="kpi-settings"
        >
          <v-menu location="bottom">
            <template #activator="{ props }">
              <v-btn v-bind="props" size="small" data-tour="kpi-display-settings-btn">
                <v-icon>mdi-menu</v-icon>
              </v-btn>
            </template>
            <v-list
              class="py-0"
              density="compact"
              width="190px"
              data-tour="kpi-display-settings-list"
            >
              <v-list-item class="menu-item" @click="showModalPositionDataOffset = true">
                <v-list-item-title class="d-flex justify-space-between">
                  {{ $t("position_data.display_settings.offset") }}
                </v-list-item-title>
              </v-list-item>

              <v-list-item class="menu-item" @click="topViewStore.viewMirrorXY">
                <v-list-item-title class="d-flex justify-space-between">
                  {{ $t("position_data.display_settings.mirror_xy") }}
                  <tab-window-icon
                    :class="{
                      'text-disabled': !topViewStore.mirrorXY,
                      'text-red': topViewStore.mirrorXY,
                    }"
                  >
                    mdi-check
                  </tab-window-icon>
                </v-list-item-title>
              </v-list-item>

              <v-divider />

              <v-menu location="end" open-on-hover>
                <template #activator="{ props }">
                  <v-list-item v-bind="props" class="menu-item">
                    <v-list-item-title class="d-flex justify-space-between">
                      {{ $t("visualization.kpi.view_mode.title") }}
                      <tab-window-icon>mdi-chevron-right</tab-window-icon>
                    </v-list-item-title>
                  </v-list-item>
                </template>
                <v-list class="py-0" density="compact" width="100px">
                  <v-list-item class="menu-item" @click="viewMode = 'table'">
                    <v-list-item-title class="d-flex justify-space-between">
                      {{ $t("visualization.kpi.view_mode.table") }}
                      <tab-window-icon
                        :class="{
                          'text-disabled': viewMode !== 'table',
                          'text-red': viewMode === 'table',
                        }"
                      >
                        mdi-check
                      </tab-window-icon>
                    </v-list-item-title>
                  </v-list-item>
                  <v-list-item class="menu-item" @click="viewMode = 'chart'">
                    <v-list-item-title class="d-flex justify-space-between">
                      {{ $t("visualization.kpi.view_mode.chart") }}
                      <tab-window-icon
                        :class="{
                          'text-disabled': viewMode !== 'chart',
                          'text-red': viewMode === 'chart',
                        }"
                      >
                        mdi-check
                      </tab-window-icon>
                    </v-list-item-title>
                  </v-list-item>
                </v-list>
              </v-menu>

              <v-menu location="end" open-on-hover>
                <template #activator="{ props }">
                  <v-list-item v-bind="props" class="menu-item">
                    <v-list-item-title class="d-flex justify-space-between">
                      {{ $t("visualization.kpi.group_mode.title") }}
                      <tab-window-icon>mdi-chevron-right</tab-window-icon>
                    </v-list-item-title>
                  </v-list-item>
                </template>
                <v-list class="py-0" density="compact" width="100px">
                  <v-list-item class="menu-item" @click="groupMode = 'player'">
                    <v-list-item-title class="d-flex justify-space-between">
                      {{ $t("visualization.kpi.group_mode.player") }}
                      <tab-window-icon
                        :class="{
                          'text-disabled': groupMode !== 'player',
                          'text-red': groupMode === 'player',
                        }"
                      >
                        mdi-check
                      </tab-window-icon>
                    </v-list-item-title>
                  </v-list-item>
                  <v-list-item class="menu-item" @click="groupMode = 'team'">
                    <v-list-item-title class="d-flex justify-space-between">
                      {{ $t("visualization.kpi.group_mode.team") }}
                      <tab-window-icon
                        :class="{
                          'text-disabled': groupMode !== 'team',
                          'text-red': groupMode === 'team',
                        }"
                      >
                        mdi-check
                      </tab-window-icon>
                    </v-list-item-title>
                  </v-list-item>
                </v-list>
              </v-menu>

              <v-list-item class="menu-item" @click="showModalPositionDataEntityColors = true">
                <v-list-item-title class="d-flex justify-space-between">
                  {{ $t("position_data.display_settings.entity_colors") }}
                </v-list-item-title>
              </v-list-item>

              <v-menu
                v-model="kpiMenuOpen"
                location="end"
                open-on-hover
                :close-on-content-click="false"
              >
                <template #activator="{ props }">
                  <v-list-item v-bind="props" class="menu-item">
                    <v-list-item-title class="d-flex justify-space-between">
                      {{ $t("visualization.kpi.kpi_selection.title") }}
                      <tab-window-icon>mdi-chevron-right</tab-window-icon>
                    </v-list-item-title>
                  </v-list-item>
                </template>

                <v-list
                  class="py-0"
                  density="compact"
                  :width="viewMode === 'chart' ? '160px' : '280px'"
                >
                  <!-- Chart mode: nested submenu per KPI group -->
                  <template v-if="viewMode === 'chart'">
                    <template v-for="group in chartKpiGroups" :key="group.key">
                      <v-menu location="end" open-on-hover>
                        <template #activator="{ props: groupProps }">
                          <v-list-item v-bind="groupProps" class="menu-item">
                            <v-list-item-title class="d-flex justify-space-between">
                              {{ $t(group.labelKey) }}
                              <tab-window-icon>mdi-chevron-right</tab-window-icon>
                            </v-list-item-title>
                          </v-list-item>
                        </template>
                        <v-list class="py-0" density="compact" :width="group.chartWidth">
                          <template v-if="group.key === 'velocity'">
                            <v-list-item class="menu-item" @click.stop>
                              <v-list-item-title class="d-flex align-center justify-space-between">
                                <span>{{ $t("visualization.kpi.kpi_selection.unit") }}</span>
                                <v-btn-toggle
                                  v-model="velocityUnit"
                                  mandatory
                                  density="compact"
                                  color="primary"
                                  border
                                  style="height: 22px"
                                >
                                  <v-btn
                                    value="ms"
                                    size="x-small"
                                    style="font-size: 11px; padding: 0 6px"
                                    >m/s</v-btn
                                  >
                                  <v-btn
                                    value="kmh"
                                    size="x-small"
                                    style="font-size: 11px; padding: 0 6px"
                                    >km/h</v-btn
                                  >
                                </v-btn-toggle>
                              </v-list-item-title>
                            </v-list-item>
                            <v-divider />
                          </template>
                          <template v-for="option in group.options" :key="option.id">
                            <v-list-item class="menu-item" @click="toggleKpi(option)">
                              <v-list-item-title class="d-flex justify-space-between">
                                <template v-if="option.mode === 'windowed'">
                                  <span class="d-flex align-center" style="gap: 2px">
                                    <span
                                      v-html="
                                        splitWindowedLabel(
                                          group.key === 'velocity'
                                            ? option.id + '_short'
                                            : option.id
                                        ).before
                                      "
                                    />
                                    <input
                                      v-model.number="windowFrames"
                                      type="number"
                                      min="1"
                                      class="inline-frame-input"
                                      :style="{ width: inputWidth }"
                                      @click.stop
                                      @keydown.stop
                                      @blur="onFrameInputBlur"
                                    />
                                    <span
                                      v-html="
                                        splitWindowedLabel(
                                          group.key === 'velocity'
                                            ? option.id + '_short'
                                            : option.id
                                        ).after
                                      "
                                    />
                                  </span>
                                </template>
                                <span
                                  v-else
                                  v-html="
                                    $t(
                                      `visualization.kpi.kpi_selection.${
                                        group.key === 'velocity' ? option.id + '_short' : option.id
                                      }`
                                    )
                                  "
                                />
                                <tab-window-icon
                                  :class="{
                                    'text-disabled': !isKpiSelected(option),
                                    'text-red': isKpiSelected(option),
                                  }"
                                >
                                  mdi-check
                                </tab-window-icon>
                              </v-list-item-title>
                            </v-list-item>
                          </template>
                        </v-list>
                      </v-menu>
                    </template>
                  </template>

                  <!-- Table mode: flat list -->
                  <template v-else>
                    <template v-for="option in kpiOptions" :key="option.id">
                      <v-list-item class="menu-item" @click="toggleKpi(option)">
                        <v-list-item-title class="d-flex align-center">
                          <span
                            style="flex: 1; min-width: 0"
                            v-html="
                              $t(
                                `visualization.kpi.kpi_selection.${
                                  option.kpi === 'velocity_max' ? option.id + '_short' : option.id
                                }`
                              )
                            "
                          />
                          <v-btn-toggle
                            v-if="option.kpi === 'velocity_max'"
                            v-model="velocityUnit"
                            mandatory
                            density="compact"
                            color="primary"
                            border
                            style="height: 18px; flex-shrink: 0; margin: 0 8px"
                            @click.stop
                          >
                            <v-btn value="ms" size="x-small" style="font-size: 10px; padding: 0 4px"
                              >m/s</v-btn
                            >
                            <v-btn
                              value="kmh"
                              size="x-small"
                              style="font-size: 10px; padding: 0 4px"
                              >km/h</v-btn
                            >
                          </v-btn-toggle>
                          <tab-window-icon
                            style="flex-shrink: 0"
                            :class="{
                              'text-disabled': !isKpiSelected(option),
                              'text-red': isKpiSelected(option),
                            }"
                          >
                            mdi-check
                          </tab-window-icon>
                        </v-list-item-title>
                      </v-list-item>
                    </template>
                  </template>
                </v-list>
              </v-menu>

              <v-divider />

              <v-menu location="end" open-on-hover :close-on-content-click="false">
                <template #activator="{ props }">
                  <v-list-item v-bind="props" class="menu-item">
                    <v-list-item-title class="d-flex justify-space-between">
                      {{ $t("visualization.kpi.zone_selection.title") }}
                      <tab-window-icon>mdi-chevron-right</tab-window-icon>
                    </v-list-item-title>
                  </v-list-item>
                </template>

                <ZoneSelectorPicker
                  v-model="selectedZones"
                  :sport="topViewStore.currentSport"
                  :area-size="topViewStore.currentAreaSize"
                  :mirror-x-y="topViewStore.mirrorXY"
                />
              </v-menu>

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
          <ModalPositionDataOffset
            v-if="showModalPositionDataOffset"
            v-model="showModalPositionDataOffset"
          />

          <v-btn v-if="viewMode === 'chart'" size="small" @click="kpiChartRef?.saveChart()">
            <v-icon>mdi-download</v-icon>
          </v-btn>

          <v-menu location="bottom">
            <template #activator="{ props }">
              <v-btn v-bind="props" size="small" class="mr-2">
                <v-icon size="small">mdi-timer-sync-outline</v-icon>
              </v-btn>
            </template>

            <v-list class="py-0" density="compact" width="250px">
              <v-list-item
                class="menu-item"
                @click="positionDataStore.setSelectedTimeRangeStart(playerStore.currentTime)"
              >
                <v-list-item-title>
                  {{ $t("visualization.time_selection.sync_start") }}
                </v-list-item-title>
              </v-list-item>

              <v-list-item
                class="menu-item"
                @click="positionDataStore.setSelectedTimeRangeEnd(playerStore.currentTime)"
              >
                <v-list-item-title>
                  {{ $t("visualization.time_selection.sync_end") }}
                </v-list-item-title>
              </v-list-item>

              <v-divider />

              <v-list-item
                class="menu-item"
                @click="
                  positionDataStore.setSelectedTimeRangeStart(allFrameKeys[0]);
                  positionDataStore.setSelectedTimeRangeEnd(allFrameKeys[allFrameKeys.length - 1]);
                "
              >
                <v-list-item-title>
                  {{ $t("visualization.time_selection.full_match") }}
                </v-list-item-title>
              </v-list-item>

              <v-list-item
                class="menu-item"
                @click="
                  positionDataStore.setSelectedTimeRangeStart(findFirstFrameWithHalftime(1));
                  positionDataStore.setSelectedTimeRangeEnd(findLastFrameWithHalftime(1));
                "
                :disabled="!visualizationStore.halftimesExist"
              >
                <v-list-item-title>
                  {{ $t("visualization.time_selection.first_half") }}
                </v-list-item-title>
              </v-list-item>

              <v-list-item
                class="menu-item"
                @click="
                  positionDataStore.setSelectedTimeRangeStart(findFirstFrameWithHalftime(2));
                  positionDataStore.setSelectedTimeRangeEnd(findLastFrameWithHalftime(2));
                "
                :disabled="!visualizationStore.halftimesExist"
              >
                <v-list-item-title>
                  {{ $t("visualization.time_selection.second_half") }}
                </v-list-item-title>
              </v-list-item>
            </v-list>
          </v-menu>
        </v-col>
        <v-col class="pa-0">
          <VisualizationTimeSelector class="ml-n2" />
        </v-col>
      </v-row>
    </div>

    <div
      v-if="viewMode === 'table'"
      data-tour="kpi-table-view"
      class="mt-n3"
      :class="{ 'kpi-table-view--fill': dense }"
    >
      <div v-if="groupMode === 'player'" class="team-tables mx-n2">
        <v-card
          v-for="(teamPlayers, teamId) in runningDistanceTeamItems"
          :key="teamId"
          class="team-card"
          outlined
          :style="{ backgroundColor: toRgb(visualizationStore.getTeamColor(teamId), 0.8) }"
        >
          <v-card-title class="text-center mt-n1">{{ getTeamName(teamId) }}</v-card-title>

          <div class="player-selector mb-3">
            <div
              v-for="p in playerOptions.filter((p) => p.teamId == teamId)"
              :key="p.playerId"
              class="player-dot"
              :style="{
                backgroundColor: selectedPlayerIds.has(p.playerId)
                  ? toRgb(playerColors[p.playerId], 0)
                  : toRgb(playerColors[p.playerId], 0.6),
                color: selectedPlayerIds.has(p.playerId) ? '#fff' : '#222',
                borderColor: selectedPlayerIds.has(p.playerId)
                  ? toRgb(playerColors[p.playerId], 0)
                  : toRgb(playerColors[p.playerId], 0.6),
              }"
              @click="togglePlayerId(p.playerId)"
            >
              {{ getPlayerNumber(p.playerId) }}
            </div>
          </div>

          <div class="kpi-table-fill kpi-table-pad--half">
            <v-data-table
              color="primary"
              :headers="playerHeaders"
              :items="teamPlayers"
              :items-per-page="-1"
              class="elevation-2 kpi-table-grow kpi-table-sticky-first-col"
              hide-default-footer
              density="compact"
              :fixed-header="dense"
            >
              <template #item="{ item, columns }">
                <tr
                  :style="{
                    backgroundColor: toRgb(visualizationStore.getTeamColor(item.team_id), 0.6),
                  }"
                >
                  <td v-for="col in columns" :key="col.key">
                    {{
                      col.key === "player_id"
                        ? getPlayerNumber(item[col.key])
                        : item[col.key] ?? "-"
                    }}
                  </td>
                </tr>
              </template>

              <template #body.append>
                <tr
                  :style="{
                    fontWeight: 'bold',
                    backgroundColor: toRgb(visualizationStore.getTeamColor(teamId), 0.45),
                  }"
                >
                  <td>{{ $t("visualization.kpi.player_view.best") }}</td>
                  <td v-for="col in playerHeaders.slice(1)" :key="col.key">
                    {{ getColBest(teamPlayers, col.key) }}
                  </td>
                </tr>
                <tr
                  :style="{
                    fontWeight: 'bold',
                    backgroundColor: toRgb(visualizationStore.getTeamColor(teamId), 0.45),
                  }"
                >
                  <td>{{ $t("visualization.kpi.player_view.total") }}</td>
                  <td v-for="col in playerHeaders.slice(1)" :key="col.key">
                    {{ getColTotal(teamPlayers, col.key) }}
                  </td>
                </tr>
              </template>

              <template #header.velocity_max="{ column }">
                <span v-html="column.title" />
              </template>
              <template #header.metabolic_work="{ column }">
                <span v-html="column.title" />
              </template>
              <template #header.centroid_distance_max="{ column }">
                <span v-html="column.title" />
              </template>
            </v-data-table>
          </div>
        </v-card>
      </div>

      <div v-else class="team-tables mx-n2">
        <v-card
          v-for="teamRow in runningDistanceTeamAggregated"
          :key="teamRow.team_id"
          class="team-card"
          outlined
          :style="{ backgroundColor: toRgb(visualizationStore.getTeamColor(teamRow.team_id), 0.8) }"
        >
          <v-card-title class="text-center mt-n1">{{ getTeamName(teamRow.team_id) }}</v-card-title>

          <div class="player-selector mb-3">
            <div
              v-for="p in playerOptions.filter((p) => p.teamId == teamRow.team_id)"
              :key="p.playerId"
              class="player-dot"
              :style="{
                backgroundColor: selectedPlayerIds.has(p.playerId)
                  ? toRgb(playerColors[p.playerId], 0)
                  : toRgb(playerColors[p.playerId], 0.6),
                color: selectedPlayerIds.has(p.playerId) ? '#fff' : '#222',
                borderColor: selectedPlayerIds.has(p.playerId)
                  ? toRgb(playerColors[p.playerId], 0)
                  : toRgb(playerColors[p.playerId], 0.6),
              }"
              @click="togglePlayerId(p.playerId)"
            >
              {{ getPlayerNumber(p.playerId) }}
            </div>
          </div>

          <div class="kpi-table-fill kpi-table-pad">
            <v-data-table
              color="primary"
              :headers="teamHeaders"
              :items="teamRow.rows"
              :items-per-page="-1"
              class="elevation-2 kpi-table-grow"
              hide-default-footer
              density="compact"
              :fixed-header="dense"
            >
              <template #item="{ item }">
                <tr
                  :style="{
                    backgroundColor: toRgb(visualizationStore.getTeamColor(teamRow.team_id), 0.6),
                  }"
                >
                  <td><span v-html="item.label" /></td>
                  <td>{{ item.total ?? "-" }}</td>
                  <td>{{ item.avg ?? "-" }}</td>
                </tr>
              </template>
            </v-data-table>
          </div>
        </v-card>
      </div>
    </div>

    <div v-else-if="viewMode === 'chart'" class="px-2 mt-2" data-tour="kpi-chart-view">
      <KpiChart
        ref="kpiChartRef"
        :selectedPlayerIds="selectedPlayerIds"
        :selectedKpi="chartKpi"
        :groupMode="groupMode"
        :chartMode="chartMode"
        :windowSize="chartWindowSize"
        :windowFrames="windowFrames"
        :playerOptions="playerOptions"
        :playerColors="playerColors"
        :selectedZones="selectedZones"
        :velocityUnit="velocityUnit"
      />

      <div class="chart-legend mt-7" :class="{ 'chart-legend--dense': dense }">
        <div v-for="(players, teamId) in teamGroups" :key="teamId" class="chart-legend-team">
          <div
            class="team-dot"
            :style="{
              backgroundColor: isTeamFullySelected(teamId)
                ? toRgb(visualizationStore.getTeamColor(teamId), 0)
                : 'transparent',
              color: isTeamFullySelected(teamId)
                ? '#fff'
                : toRgb(visualizationStore.getTeamColor(teamId), 0),
              borderColor: toRgb(visualizationStore.getTeamColor(teamId), 0),
            }"
            @click="toggleTeam(teamId)"
          >
            {{ getTeamName(teamId) }}
          </div>
          <span class="chart-legend-sep">|</span>
          <div
            v-for="p in players"
            :key="p.playerId"
            class="player-dot"
            :style="{
              backgroundColor: selectedPlayerIds.has(p.playerId)
                ? toRgb(playerColors[p.playerId], 0)
                : toRgb(playerColors[p.playerId], 0.6),
              color: selectedPlayerIds.has(p.playerId) ? '#fff' : '#222',
              borderColor: selectedPlayerIds.has(p.playerId)
                ? toRgb(playerColors[p.playerId], 0)
                : toRgb(playerColors[p.playerId], 0.6),
            }"
            @click="togglePlayerId(p.playerId)"
          >
            {{ getPlayerNumber(p.playerId) }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, toRaw, onBeforeUnmount } from "vue";
// viewMode is driven by tabStore.kpiViewMode so the tutorial can switch views externally
import { useVisualizationStore } from "@/stores/visualization";
import { useTopViewStore } from "@/stores/top_view";
import { usePositionDataStore } from "@/stores/position_data";
import { usePlayerStore } from "@/stores/player";
import { useVideoStore } from "@/stores/video";
import { usePosdataWorkerStore } from "@/stores/posdata_worker";
import { useTabStore } from "@/stores/tabs";
import { useUserStore } from "@/stores/user";
import VisualizationTimeSelector from "@/components/visualization/VisualizationTimeSelector.vue";
import KpiChart from "@/components/kpi/KpiChart.vue";
import ZoneSelectorPicker from "@/components/kpi/ZoneSelectorPicker.vue";
import ModalPositionDataSelect from "@/components/position-data/ModalPositionDataSelect.vue";
import ModalPositionDataUpload from "@/components/position-data/ModalPositionDataUpload.vue";
import ModalPositionDataEntityColors from "@/components/position-data/ModalPositionDataEntityColors.vue";
import ModalPositionDataOffset from "@/components/position-data/ModalPositionDataOffset.vue";
import { useI18n } from "vue-i18n";
import { toRgb } from "@/plugins/helpers";
import { debounce } from "lodash";
import { isInSportZone, allSportZones } from "@/plugins/sport_zones";

defineProps({
  // True when this widget shares its row with video/topview and has been
  // height-capped to their size (see DashboardGrid) — keep team tables
  // side by side with horizontal scroll instead of wrapping to new lines,
  // and let each table scroll its own rows once it hits the cap.
  dense: { type: Boolean, default: false },
});

const topViewStore = useTopViewStore();
const visualizationStore = useVisualizationStore();
const positionDataStore = usePositionDataStore();
const playerStore = usePlayerStore();
const videoStore = useVideoStore();
const posdataWorkerStore = usePosdataWorkerStore();
const tabStore = useTabStore();
const userStore = useUserStore();

const { t } = useI18n();

const canWrite = computed(() => {
  if (userStore.role === "admin") return true;
  const ownerUsername = playerStore.video?.owner_username;
  if (!ownerUsername) return true;
  return ownerUsername === userStore.username;
});

const kpiPosdataNotSelectedText = computed(() => {
  const full = t("visualization.kpi.posdata_not_selected");
  return canWrite.value ? full : full.split("<br>")[0];
});

const kpiNotSelectedText = computed(() => {
  const full = t("visualization.kpi.kpi_not_selected");
  return canWrite.value ? full : full.split("<br>")[0];
});

const kpiChartRef = ref(null);

// Split a windowed locale string at the {frames} placeholder so each half
// can be rendered with v-html (preserving <sub>/<sup> tags).
const splitWindowedLabel = (optionId) => {
  const SENTINEL = "\u0001";
  const msg = t(`visualization.kpi.kpi_selection.${optionId}`, { frames: SENTINEL });
  const idx = msg.indexOf(SENTINEL);
  if (idx === -1) return { before: msg, after: "" };
  return { before: msg.slice(0, idx), after: msg.slice(idx + 1) };
};

const viewMode = computed({
  get: () => tabStore.kpiViewMode,
  set: (val) => {
    tabStore.kpiViewMode = val;
  },
});
const groupMode = computed({
  get: () => visualizationStore.kpiGroupMode,
  set: (val) => {
    visualizationStore.kpiGroupMode = val;
  },
});

const showModalPositionDataSelect = ref(false);
const showModalPositionDataUpload = ref(false);
const showModalPositionDataEntityColors = ref(false);
const showModalPositionDataOffset = ref(false);

// Zone initialization based on current sport
const LONG_BOUNDS = [0, 0.2025, 0.365, 0.635, 0.7955, 1];
const TRANS_BOUNDS = [0, 0.1575, 0.33, 0.67, 0.8425, 1];
function _soccerAllZones() {
  const zones = [];
  for (let r = 0; r < 5; r++)
    for (let c = 0; c < 5; c++)
      zones.push({
        x0: TRANS_BOUNDS[c],
        y0: LONG_BOUNDS[r],
        x1: TRANS_BOUNDS[c + 1],
        y1: LONG_BOUNDS[r + 1],
      });
  return zones;
}
function _defaultZonesForSport(sportKey) {
  if (sportKey === "handball" || sportKey === "basketball") return allSportZones(sportKey);
  return _soccerAllZones();
}
if (visualizationStore.kpiSelectedZones === null) {
  visualizationStore.kpiSelectedZones = _defaultZonesForSport(topViewStore.currentSport?.key);
}
const selectedZones = computed({
  get: () => visualizationStore.kpiSelectedZones,
  set: (val) => {
    visualizationStore.kpiSelectedZones = val;
  },
});
watch(
  () => topViewStore.currentSport?.key,
  (newKey) => {
    selectedZones.value = _defaultZonesForSport(newKey);
  }
);

// Maps kpi_names (from kpi_computation meta_data) → display options per view mode.
const KPI_CONFIG = {
  distance_covered: {
    labelKey: "visualization.kpi.kpi_selection.group_distance",
    chartWidth: "230px",
    chart: [
      { id: "running_distance_frame", kpi: "running_distance", mode: "per_frame" },
      { id: "running_distance_interval", kpi: "running_distance", mode: "windowed" },
      { id: "running_distance_cumulative", kpi: "running_distance", mode: "cumulative" },
    ],
    table: [{ id: "running_distance_cumulative", kpi: "running_distance", mode: "cumulative" }],
  },
  velocity: {
    labelKey: "visualization.kpi.kpi_selection.group_velocity",
    chartWidth: "190px",
    chart: [
      { id: "velocity_frame", kpi: "velocity", mode: "per_frame" },
      { id: "velocity_interval", kpi: "velocity", mode: "windowed" },
    ],
    table: [{ id: "velocity_max", kpi: "velocity_max", mode: "cumulative" }],
  },
  metabolic_power: {
    labelKey: "visualization.kpi.kpi_selection.group_metabolic_work",
    chartWidth: "280px",
    chart: [
      { id: "metabolic_work_frame", kpi: "metabolic_work", mode: "per_frame" },
      { id: "metabolic_work_interval", kpi: "metabolic_work", mode: "windowed" },
      { id: "metabolic_work_cumulative", kpi: "metabolic_work", mode: "cumulative" },
    ],
    table: [{ id: "metabolic_work_cumulative", kpi: "metabolic_work", mode: "cumulative" }],
  },
  equivalent_distance: {
    labelKey: "visualization.kpi.kpi_selection.group_equivalent_distance",
    chartWidth: "260px",
    chart: [
      { id: "equivalent_distance_frame", kpi: "equivalent_distance", mode: "per_frame" },
      { id: "equivalent_distance_interval", kpi: "equivalent_distance", mode: "windowed" },
      { id: "equivalent_distance_cumulative", kpi: "equivalent_distance", mode: "cumulative" },
    ],
    table: [
      { id: "equivalent_distance_cumulative", kpi: "equivalent_distance", mode: "cumulative" },
    ],
  },
  centroid_distance: {
    labelKey: "visualization.kpi.kpi_selection.group_centroid_distance",
    chartWidth: "290px",
    chart: [
      { id: "centroid_distance_frame", kpi: "centroid_distance", mode: "per_frame" },
      { id: "centroid_distance_interval", kpi: "centroid_distance", mode: "windowed" },
    ],
    table: [{ id: "centroid_distance_max", kpi: "centroid_distance_max", mode: "table_max" }],
  },
};

// For table mode: flat list of table options for available KPI names
const kpiOptions = computed(() => {
  const names = visualizationStore.kpiNames;
  if (!names || !names.length) return [];
  return names.flatMap((name) => KPI_CONFIG[name]?.table || []);
});

// For chart mode: grouped structure for nested submenu
const chartKpiGroups = computed(() => {
  const names = visualizationStore.kpiNames;
  if (!names || !names.length) return [];
  return names
    .filter((name) => KPI_CONFIG[name])
    .map((name) => ({
      key: name,
      labelKey: KPI_CONFIG[name].labelKey,
      chartWidth: KPI_CONFIG[name].chartWidth,
      options: KPI_CONFIG[name].chart,
    }));
});

// Chart mode: single selected option (includes mode + window info)
const selectedKpiId = computed({
  get: () => visualizationStore.kpiSelectedKpiId,
  set: (val) => {
    visualizationStore.kpiSelectedKpiId = val;
  },
});
// Table mode: set of KPI ids (independent selection) — stored as an array
// (sessionStorage-serializable) and exposed here as a Set to match existing
// usage (.has/.add/.delete).
const selectedKpis = computed({
  get: () => new Set(visualizationStore.kpiSelectedKpiIds),
  set: (val) => {
    visualizationStore.kpiSelectedKpiIds = [...val];
  },
});

// User-configurable interval in frames (default: 10)
const windowFrames = computed({
  get: () => visualizationStore.kpiWindowFrames,
  set: (val) => {
    visualizationStore.kpiWindowFrames = val;
  },
});

const onFrameInputBlur = () => {
  if (!windowFrames.value || windowFrames.value < 1 || isNaN(windowFrames.value)) {
    windowFrames.value = 10;
  }
};

const inputWidth = computed(() => {
  const digits = String(windowFrames.value || "").length || 1;
  return `${Math.max(2, digits + 1)}ch`;
});

const frameDurationMs = computed(() => {
  const fps = playerStore.videoFPS || 25;
  return 1000 / fps;
});

const chartWindowSize = computed(() => {
  return Math.max(1, windowFrames.value) * frameDurationMs.value;
});

const windowTimeLabel = computed(() => {
  const totalMs = chartWindowSize.value;
  if (totalMs < 1000) return `${Math.round(totalMs)} ms`;
  const totalSec = totalMs / 1000;
  if (totalSec < 60) return `${totalSec.toFixed(1)}s`;
  const min = Math.floor(totalSec / 60);
  const sec = Math.round(totalSec % 60);
  return sec > 0 ? `${min} min ${sec}s` : `${min} min`;
});

const allChartOptions = computed(() => chartKpiGroups.value.flatMap((g) => g.options));

const selectedKpiOption = computed(
  () => allChartOptions.value.find((o) => o.id === selectedKpiId.value) || allChartOptions.value[0]
);
const chartKpi = computed(() => selectedKpiOption.value?.kpi);
const chartMode = computed(() => selectedKpiOption.value?.mode);

const kpiMenuOpen = ref(false);

const velocityUnit = computed({
  get: () => visualizationStore.kpiVelocityUnit,
  set: (val) => {
    visualizationStore.kpiVelocityUnit = val;
  },
});
const velocityFactor = computed(() => (velocityUnit.value === "kmh" ? 3.6 : 1.0));
const velocityUnitHtml = computed(() =>
  velocityUnit.value === "kmh" ? "km⋅h<sup>-1</sup>" : "m⋅s<sup>-1</sup>"
);
const hasVelocityKpi = computed(() => visualizationStore.kpiNames?.includes("velocity") ?? false);

const isKpiSelected = (option) => {
  if (viewMode.value === "chart") {
    return selectedKpiId.value === option.id;
  }
  return selectedKpis.value.has(option.id);
};

const toggleKpi = (option) => {
  if (viewMode.value === "chart") {
    selectedKpiId.value = option.id;
    kpiMenuOpen.value = false;
  } else {
    // Table: multi select by id, keep at least one
    const newSet = new Set(selectedKpis.value);
    if (newSet.has(option.id)) {
      if (newSet.size > 1) newSet.delete(option.id);
    } else {
      newSet.add(option.id);
    }
    selectedKpis.value = newSet;
  }
};

const allFrameKeys = computed(() => topViewStore.sortedFrameKeys);
const selectedStartFrame = computed(() => positionDataStore.selectedTimeRange.start);
const selectedEndFrame = computed(() => positionDataStore.selectedTimeRange.end);
const maxFrameIndex = ref(0);
watch(
  () => allFrameKeys.value,
  (keys) => {
    selectedStartFrame.value = keys[0];
    selectedEndFrame.value = keys[keys.length - 1];
    maxFrameIndex.value = keys[keys.length - 1];
  }
);

const playerHeaders = computed(() => {
  const cols = [{ title: t("visualization.kpi.player_view.player_id"), key: "player_id" }];
  if (selectedKpis.value.has("running_distance_cumulative")) {
    cols.push({ title: t("visualization.kpi.kpi_label.distance"), key: "distance" });
  }
  if (selectedKpis.value.has("velocity_max")) {
    cols.push({
      title: t("visualization.kpi.kpi_label.velocity_max_with_unit", {
        unit: velocityUnitHtml.value,
      }),
      key: "velocity_max",
    });
  }
  if (selectedKpis.value.has("metabolic_work_cumulative")) {
    cols.push({ title: t("visualization.kpi.kpi_label.metabolic_work"), key: "metabolic_work" });
  }
  if (selectedKpis.value.has("equivalent_distance_cumulative")) {
    cols.push({
      title: t("visualization.kpi.kpi_label.equivalent_distance"),
      key: "equivalent_distance",
    });
  }
  if (selectedKpis.value.has("centroid_distance_max")) {
    cols.push({
      title: t("visualization.kpi.kpi_label.centroid_distance_max"),
      key: "centroid_distance_max",
    });
  }
  return cols;
});

const teamHeaders = computed(() => [
  { title: t("visualization.kpi.team_view.kpi"), key: "label" },
  { title: t("visualization.kpi.team_view.total"), key: "total" },
  { title: t("visualization.kpi.team_view.average"), key: "avg" },
]);

const playerOptions = computed(() => topViewStore.precomputedPlayerList);
// Stored as an array (sessionStorage-serializable) and exposed here as a Set
// to match existing usage (.has/.add/.delete).
const selectedPlayerIds = computed({
  get: () => new Set(visualizationStore.kpiSelectedPlayerIds ?? []),
  set: (val) => {
    visualizationStore.kpiSelectedPlayerIds = [...val];
  },
});
watch(
  playerOptions,
  (list) => {
    if (!list.length) return;
    if (visualizationStore.kpiSelectedPlayerIds === null) {
      // First time ever (nothing persisted/selected yet) — default to everyone.
      selectedPlayerIds.value = new Set(list.map((p) => p.playerId));
    } else {
      // Keep the persisted/current selection, dropping any ids that no longer
      // exist in this dataset (e.g. switched to a different video's tracking
      // data) — falling back to "everyone" if that leaves nothing selected.
      const available = new Set(list.map((p) => p.playerId));
      const filtered = new Set([...selectedPlayerIds.value].filter((id) => available.has(id)));
      selectedPlayerIds.value = filtered.size > 0 ? filtered : new Set(list.map((p) => p.playerId));
    }
  },
  { immediate: true }
);
const playerColors = computed(() => {
  const map = {};
  for (const p of playerOptions.value) {
    map[p.playerId] = visualizationStore.getTeamColor(p.teamId);
  }
  return map;
});
const togglePlayerId = (playerId) => {
  const newSet = new Set(selectedPlayerIds.value);
  if (newSet.has(playerId)) {
    newSet.delete(playerId);
  } else {
    newSet.add(playerId);
  }
  selectedPlayerIds.value = newSet;
};

const teamGroups = computed(() => {
  const groups = {};
  for (const p of playerOptions.value) {
    if (!groups[p.teamId]) groups[p.teamId] = [];
    groups[p.teamId].push(p);
  }
  return groups;
});

const toggleTeam = (teamId) => {
  const teamPlayerIds = (teamGroups.value[teamId] || []).map((p) => p.playerId);
  const allSelected = teamPlayerIds.every((pid) => selectedPlayerIds.value.has(pid));
  const newSet = new Set(selectedPlayerIds.value);
  if (allSelected) {
    teamPlayerIds.forEach((pid) => newSet.delete(pid));
  } else {
    teamPlayerIds.forEach((pid) => newSet.add(pid));
  }
  selectedPlayerIds.value = newSet;
};

const isTeamFullySelected = (teamId) => {
  const teamPlayerIds = (teamGroups.value[teamId] || []).map((p) => p.playerId);
  return teamPlayerIds.length > 0 && teamPlayerIds.every((pid) => selectedPlayerIds.value.has(pid));
};

const isInAnyZone = (x, y, zones) => {
  if (!zones || zones.length === 0) return false;
  for (const z of zones) {
    if (z.sportZone) {
      if (isInSportZone(z.sportKey, z.zoneId, x, y)) return true;
      continue;
    }
    if (x >= z.x0 && x <= z.x1 && y >= z.y0 && y <= z.y1) return true;
  }
  return false;
};

const kpiItems = ref([]);
const _triggerKpiCalc = debounce(async () => {
  const rawKpiData = toRaw(visualizationStore.kpiData);
  if (!rawKpiData || typeof rawKpiData !== "object" || !Object.keys(rawKpiData).length) {
    kpiItems.value = [];
    return;
  }
  const startMs = selectedStartFrame.value;
  const endMs = selectedEndFrame.value;
  const posData = topViewStore.getSubsetObject(startMs, endMs);
  try {
    const result = await posdataWorkerStore.calcKpiAggregation(
      rawKpiData,
      posData,
      selectedPlayerIds.value,
      startMs,
      endMs,
      toRaw(selectedZones.value),
      visualizationStore.kpiFramerate || 25
    );
    kpiItems.value = result;
  } catch (err) {
    console.error("Worker KPI aggregation failed:", err);
    kpiItems.value = [];
  }
}, 150);
watch(
  [
    selectedPlayerIds,
    selectedStartFrame,
    selectedEndFrame,
    selectedZones,
    () => visualizationStore.kpiData,
  ],
  () => _triggerKpiCalc(),
  { immediate: true }
);
onBeforeUnmount(() => _triggerKpiCalc.cancel());

const runningDistanceTeamItems = computed(() => {
  const grouped = {};
  playerOptions.value.forEach((p) => {
    if (!grouped[p.teamId]) grouped[p.teamId] = [];
  });

  const kpiMap = {};
  kpiItems.value.forEach((item) => {
    kpiMap[item.player_id] = item;
  });

  playerOptions.value.forEach((p) => {
    if (!selectedPlayerIds.value.has(p.playerId)) return;
    const kpiItem = kpiMap[p.playerId];
    grouped[p.teamId].push(
      kpiItem
        ? {
            ...kpiItem,
            velocity_max:
              kpiItem.velocity_max != null
                ? parseFloat((kpiItem.velocity_max * velocityFactor.value).toFixed(2))
                : null,
            team_id: p.teamId,
          }
        : {
            player_id: p.playerId,
            team_id: p.teamId,
            distance: null,
            velocity_max: null,
            metabolic_work: null,
            equivalent_distance: null,
            centroid_distance_max: null,
          }
    );
  });

  return grouped;
});

const runningDistanceTeamAggregated = computed(() => {
  const result = [];
  for (const [teamId, players] of Object.entries(runningDistanceTeamItems.value)) {
    const rows = [];

    if (selectedKpis.value.has("running_distance_cumulative")) {
      const vals = players.map((p) => p.distance).filter((v) => v != null);
      const total = vals.length > 0 ? parseFloat(vals.reduce((a, b) => a + b, 0).toFixed(1)) : "-";
      const avg =
        vals.length > 0
          ? parseFloat((vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(1))
          : "-";
      rows.push({ label: t("visualization.kpi.kpi_label.distance"), total, avg });
    }

    if (selectedKpis.value.has("velocity_max")) {
      const vals = players.map((p) => p.velocity_max).filter((v) => v != null);
      const total = vals.length > 0 ? parseFloat(Math.max(...vals).toFixed(2)) : "-";
      const avg =
        vals.length > 0
          ? parseFloat((vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(2))
          : "-";
      rows.push({ label: t("visualization.kpi.kpi_label.velocity_max"), total, avg });
    }

    if (selectedKpis.value.has("metabolic_work_cumulative")) {
      const vals = players.map((p) => p.metabolic_work).filter((v) => v != null);
      const total = vals.length > 0 ? parseFloat(vals.reduce((a, b) => a + b, 0).toFixed(1)) : "-";
      const avg =
        vals.length > 0
          ? parseFloat((vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(1))
          : "-";
      rows.push({ label: t("visualization.kpi.kpi_label.metabolic_work"), total, avg });
    }

    if (selectedKpis.value.has("equivalent_distance_cumulative")) {
      const vals = players.map((p) => p.equivalent_distance).filter((v) => v != null);
      const total = vals.length > 0 ? parseFloat(vals.reduce((a, b) => a + b, 0).toFixed(1)) : "-";
      const avg =
        vals.length > 0
          ? parseFloat((vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(1))
          : "-";
      rows.push({ label: t("visualization.kpi.kpi_label.equivalent_distance"), total, avg });
    }

    if (selectedKpis.value.has("centroid_distance_max")) {
      const vals = players.map((p) => p.centroid_distance_max).filter((v) => v != null);
      const total = vals.length > 0 ? parseFloat(Math.max(...vals).toFixed(2)) : "-";
      const avg =
        vals.length > 0
          ? parseFloat((vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(2))
          : "-";
      rows.push({ label: t("visualization.kpi.kpi_label.centroid_distance_max"), total, avg });
    }

    result.push({ team_id: teamId, rows });
  }
  return result;
});

const hasPositionData = computed(() => topViewStore.sortedFrameKeys.length > 0);

const hasKpiData = computed(
  () =>
    visualizationStore.kpiData != null &&
    typeof visualizationStore.kpiData === "object" &&
    Object.keys(visualizationStore.kpiData).length > 0
);

const getTeamName = (teamId) => {
  const meta = topViewStore.metaDataTopView;
  if (meta?.team_ids?.[teamId]?.name) return meta.team_ids[teamId].name;
  return teamId;
};

const getPlayerNumber = (playerId) => {
  const meta = topViewStore.metaDataTopView;
  const num = meta?.player_ids?.[playerId]?.number;
  return num != null ? num : playerId;
};

const getColBest = (players, colKey) => {
  if (!players || !players.length) return "-";
  const vals = players.map((p) => p[colKey]).filter((v) => v != null);
  if (!vals.length) return "-";
  return parseFloat(Math.max(...vals).toFixed(2));
};

const getColTotal = (players, colKey) => {
  if (!players || !players.length) return "-";
  const vals = players.map((p) => p[colKey]).filter((v) => v != null);
  if (!vals.length) return "-";
  if (colKey === "velocity_max" || colKey === "centroid_distance_max") {
    return parseFloat(Math.max(...vals).toFixed(2));
  }
  return parseFloat(vals.reduce((a, b) => a + b, 0).toFixed(1));
};

const findFirstFrameWithHalftime = (half) => {
  const b = topViewStore.precomputedHalftimeBoundaries[half];
  return b ? b.first : 0;
};

const findLastFrameWithHalftime = (half) => {
  const b = topViewStore.precomputedHalftimeBoundaries[half];
  return b ? b.last : 0;
};
</script>

<style scoped>
.kpi-loading-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 25vh;
}

.kpi-spinner {
  font-size: 48px;
  color: rgb(var(--v-theme-primary));
}

.kpi-loading-text {
  margin-top: 10px;
  font-size: 18px;
  color: rgb(var(--v-theme-primary));
}

.card-header-zone {
  height: 56px;
  display: flex;
  align-items: center;
  flex-shrink: 0;
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

/* Capped to 2 rows of player dots (24px dot + 5px row gap); once a team
   has more players than fit, this scrolls vertically instead of growing
   into a third row. */
.player-selector {
  display: flex;
  flex-wrap: wrap;
  align-content: flex-start;
  gap: 5px;
  justify-content: center;
  margin-bottom: 8px;
  max-height: 53px;
  overflow-x: auto;
}
.player-dot {
  height: 24px;
  border-radius: 50%;
  padding: 0 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 0.7rem;
  cursor: pointer;
  border: 2px solid;
  transition: background 0.2s, border 0.2s;
  user-select: none;
  white-space: nowrap;
}
.player-dot.selected {
  border: 2px solid;
}

.inline-frame-input {
  min-width: 2ch;
  text-align: center;
  border: none;
  border-bottom: 1.5px solid rgba(var(--v-theme-primary));
  outline: none;
  font-size: 12px;
  padding: 0 2px;
  background: transparent;
  appearance: textfield;
}
.inline-frame-input::-webkit-outer-spin-button,
.inline-frame-input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
.inline-frame-input:focus {
  border-bottom-color: #1976d2;
}

/* dense (see `dense` prop): the widget's own height is capped to fit next
   to video/topview (DashboardCell's ".dashboard-cell-content--scroll" sets
   height: 100% on our ancestor) — propagate that fixed height down through
   the flex chain so .team-tables below gets a real, bounded height instead
   of growing with its content. Only applied when dense: in the normal
   (non-capped) layout the widget still just grows with its content. */
.kpi-fill-height {
  height: 100%;
  min-height: 0;
}

.kpi-table-view--fill {
  flex: 1 1 335px;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

/* Tables always stay side by side, never wrapping to a new line — once
   there are too many teams to fit, this scrolls horizontally instead.
   Grid (not flex) is deliberate: grid-template-rows gives every team-card
   below three shared row tracks (title / player-selector / table) instead
   of each card sizing those independently, which is what lets the rows
   line up across cards (see .team-card's subgrid) and lets the table row
   fill exactly down to the same bottom edge in every column.
   flex: 1 1 auto (only takes effect when dense, i.e. when the parent
   .kpi-table-view--fill is actually a flex column) makes this grid claim
   the rest of that column's height instead of sizing to its own content —
   without it the team-aggregated table (a handful of KPI rows, far
   shorter than the video/topview card it shares a row with) left a big
   unused gap below the cards instead of growing to match. */
.team-tables {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(335px, 1fr);
  grid-template-rows: auto auto 1fr;
  column-gap: 16px;
  overflow-x: auto;
  padding-bottom: 4px;
  flex: 1 1 auto;
  min-height: 0;
}

.team-card {
  /* subgrid: reuses .team-tables' 3 row tracks instead of sizing its own
     title/player-selector/table rows independently — that's what makes
     the player-selector row (and therefore the table's start/end) line
     up across every team's card. min-height: 0 lets the table row (1fr)
     actually shrink to the track size instead of growing with content.
     min-width: 0 does the equivalent on the column axis: without it a
     grid item's automatic minimum size is its content's min-content width,
     so a table with many KPI columns forces the card (and the whole
     .team-tables track) wider instead of clipping — which is what silently
     killed the table's own horizontal scrollbar (see .kpi-table-fill). */
  display: grid;
  grid-row: 1 / span 3;
  grid-template-rows: subgrid;
  min-height: 0;
  min-width: 0;
  max-width: none;
}

/* Wraps the <v-data-table> (team-card's 3rd subgrid row) instead of being
   applied to the table itself — see .kpi-table-pad below for why. Same
   min-height reset so it actually shrinks to that row's height instead of
   forcing the row (and every card sharing the subgrid track) to grow to
   fit its un-scrolled content. min-width: 0 is the matching fix on the
   column axis: it lets the wrapper shrink to the card's width instead of
   growing past its track.
   display: flex (column): gives .kpi-table-grow a genuinely definite
   height to cap against (see there) — a plain block wrapper's height,
   even though itself made definite via subgrid stretch, doesn't reliably
   keep propagating as "definite" to a nested child's percentage height
   one level further down in every browser. Note the wrapper itself still
   always fills the full subgrid row track (that's the point — every
   team's row-3 track lines up at the same height across cards), it's
   only the table *inside* it that's now allowed to be shorter (see
   .kpi-table-grow's max-height, not height). */
.kpi-table-fill {
  display: flex;
  flex-direction: column;
  min-height: 0;
  min-width: 0;
}

/* The <v-data-table> itself, inside the flex-column wrapper above.
   Deliberately flex: 0 0 auto (no grow) + max-height: 100%, not
   flex: 1 1 auto — grow would stretch every table to the wrapper's full
   height regardless of content, so a team with fewer KPI rows than its
   neighbor showed a big blank strip in the table's own opaque background
   below its last row instead of just ending there and letting the card's
   own tinted color show through. max-height still caps it at the
   wrapper's height when content *would* overflow, which is what keeps
   the table from pushing the card past the row's bounds and is what
   makes Vuetify's own `.v-table__wrapper { overflow: auto }` actually
   kick in and scroll (in both directions) once that cap is hit.
   min-height/min-width: 0 let it shrink below content size at all (flex
   items default to min-content otherwise). */
.kpi-table-grow {
  flex: 0 0 auto;
  max-height: 100%;
  min-height: 0;
  min-width: 0;
}

/* Minimal breathing room around the table only (not the whole card) —
   keeps the team name / player-selector flush like the single-player
   view while still giving the table itself a little space. Team view gets
   the full amount, the player view half (see --half), per request.
   Applied to .kpi-table-fill (a plain, background-less wrapper div around
   <v-data-table>), not to the table itself: the table (.v-table) paints
   its own opaque `--v-theme-surface` background all the way to its
   border box, so padding directly on it would just add blank space still
   filled by that background — the card's tinted color behind it would
   never actually show through. On the transparent wrapper, padding
   reveals it correctly, symmetrically on every side. */
.kpi-table-pad {
  padding: 0 8px 8px;
}
.kpi-table-pad--half {
  padding: 0 4px 4px;
}

/* Player-view table only: with many KPI columns toggled on, the table now
   scrolls horizontally on its own (see .kpi-table-fill's min-width fix) —
   pin the player-number column so it stays visible as the KPI columns
   scroll underneath it, the way a frozen row header works. :deep() is
   needed for th because default header cells are rendered by v-data-table
   itself, not by our template.

   The header cell needs a *higher* z-index than the body's sticky column,
   not the same one: Vuetify's own fixed-header CSS already gives thead
   (and its th's) position: sticky + z-index, and with an equal z-index the
   later-in-DOM element wins ties — tbody comes after thead, so on an equal
   footing the scrolling body rows painted over the pinned header instead
   of going behind it (vertical scroll), and sibling header cells (which
   Vuetify also puts at z-index: 1 in fixed-header mode) painted over our
   corner cell in DOM order too (horizontal scroll). Giving the corner th
   a clearly higher z-index (with !important, since Vuetify's own
   `.v-table--fixed-header th` rule targets the same element) fixes both:
   the corner cell now always wins, whether stacked against body rows or
   sibling header cells. */
.kpi-table-sticky-first-col :deep(th:first-child),
.kpi-table-sticky-first-col :deep(td:first-child) {
  position: sticky;
  left: 0;
}
.kpi-table-sticky-first-col :deep(td:first-child) {
  z-index: 1;
  /* Rows set their background via inline style on the <tr> — inherit picks
     that dynamic color up so the sticky cell doesn't go transparent and
     let scrolled-under cells show through. */
  background-color: inherit;
}
.kpi-table-sticky-first-col :deep(th:first-child) {
  z-index: 3 !important;
  background-color: rgb(var(--v-theme-surface)) !important;
}

.chart-legend {
  display: flex;
  justify-content: center;
  column-gap: 20px;
  row-gap: 8px;
  flex-wrap: wrap;
}

/* Squeezed next to video/topview (see `dense` prop): one row, horizontal
   scroll instead of wrapping to more lines than the capped height has
   room for — mirrors TabWindowHeatmap's chart-legend--dense. */
.chart-legend--dense {
  flex-wrap: nowrap;
  justify-content: flex-start;
  overflow-x: auto;
  padding-bottom: 4px;
}

.chart-legend-team {
  display: flex;
  align-items: center;
  gap: 5px;
}

/* Match TabWindowHeatmap's player-dot sizing (fixed 24px circle, no
   padding) in both the chart legend and the table view's player-selector —
   the base .player-dot above stays as a plain fallback, but without this
   override the table view's dots grow into pills via their padding instead
   of staying perfect circles like the other two locations. */
.chart-legend .player-dot,
.player-selector .player-dot {
  width: 24px;
  padding: 0;
  font-size: 1rem;
  white-space: normal;
}

.team-dot {
  height: 24px;
  border-radius: 50%;
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

.chart-legend-sep {
  color: #ccc;
  font-size: 18px;
  margin: 0 2px;
  user-select: none;
}
</style>
