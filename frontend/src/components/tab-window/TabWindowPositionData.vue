<template>
  <PositionDataMenu v-if="Object.keys(topViewStore.positionDataTopView).length === 0" />

  <v-container v-else class="d-flex flex-column">
    <v-row class="mt-1" justify="center">
      <div ref="topViewFullscreenRoot" class="top-view-fullscreen-root">
        <div v-if="matchupTeams.length > 1" class="matchup-overlay">
          <template v-for="(team, index) in matchupTeams" :key="team.id">
            <div class="matchup-team">
              <span class="matchup-team-name">{{ team.name }}</span>
              <span class="matchup-team-line mt-n1" :style="{ backgroundColor: team.color }" />
            </div>
            <span v-if="index < matchupTeams.length - 1" class="matchup-separator">:</span>
          </template>
        </div>

        <div class="top-view-wrapper" @mouseenter="hovering = true" @mouseleave="hovering = false">
          <img
            ref="topViewElement"
            class="visualizer-image"
            :src="topViewStore.currentSport.areaImage"
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
            v-if="isTopViewFullscreen"
            class="fullscreen-controls"
            :class="{ visible: hovering }"
          >
            <div class="controls-top">
              <v-icon @click="toggleTopView" class="control-icon">
                <template v-if="topViewEnded">mdi-restart</template>
                <template v-else-if="topViewPlaying">mdi-pause</template>
                <template v-else>mdi-play</template>
              </v-icon>
              <div class="time-code">{{ getTimecode(currentTime) }}</div>
            </div>

            <v-slider
              v-model="currentTime"
              @update:model-value="onProgressChange"
              hide-details
              color="white"
              :thumb-size="15"
              :step="1000 / playerStore.videoFPS"
              min="0"
              :max="playerStore.videoDuration"
            />
          </div>

          <svg
            v-if="topViewStore.showEffectivePlayingSpace"
            :style="{
              position: 'absolute',
              top: '0px',
              left: '0px',
              width: topViewStore.topViewSize.width + 'px',
              height: topViewStore.topViewSize.height + 'px',
            }"
          >
            <polygon
              v-for="(hull, team) in convexHullPlayer[topViewStore.currentFrameKey]"
              :key="team"
              :points="hull.map((p) => `${p.left},${p.top}`).join(' ')"
              :stroke="visualizationStore.getTeamColor(team)"
              :fill="visualizationStore.getTeamColor(team)"
              fill-opacity="0.4"
            />
          </svg>

          <svg
            v-if="topViewStore.showSpaceControl"
            :style="{
              position: 'absolute',
              top: '0px',
              left: '0px',
              width: topViewStore.topViewSize.width + 'px',
              height: topViewStore.topViewSize.height + 'px',
            }"
          >
            <polygon
              v-for="cell in voronoiCells[topViewStore.currentFrameKey]"
              :key="cell"
              :points="cell.polygon.map((p) => `${p[0]},${p[1]}`).join(' ')"
              stroke="gray"
              :fill="visualizationStore.getTeamColor(cell.team_id)"
              fill-opacity="0.4"
            />
          </svg>

          <template
            v-for="item in positionDataTransformed[topViewStore.currentFrameKey]"
            :key="item.original"
          >
            <div
              v-if="item.original[1] !== 1"
              v-show="topViewStore.showItems"
              :style="{
                position: 'absolute',
                width: '12px',
                height: '12px',
                borderRadius: '50%',
                transform: 'translate(-50%, -50%)',
                top:
                  item.transformed.y *
                    (topViewStore.topViewSize.height * topViewStore.currentSport.heightRel) +
                  ((1 - topViewStore.currentSport.heightRel) / 2) *
                    topViewStore.topViewSize.height +
                  'px',
                left:
                  item.transformed.x *
                    (topViewStore.topViewSize.width * topViewStore.currentSport.widthRel) +
                  ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width +
                  'px',
                backgroundColor: visualizationStore.getTeamColor(item.original[1]),
                cursor:
                  topViewStore.showSpaceControl || topViewStore.showEffectivePlayingSpace
                    ? 'pointer'
                    : 'default',
              }"
              @click="
                (topViewStore.showSpaceControl || topViewStore.showEffectivePlayingSpace) &&
                  togglePlayersForKPIs(item.original[0])
              "
            >
              <div
                v-if="topViewStore.showPlayerId"
                class="position-data-player-id"
                :style="{ color: visualizationStore.getTeamColor(item.original[1]) }"
              >
                {{ getPlayerNumber(item.original[0]) }}
              </div>
            </div>

            <div
              v-else
              v-show="topViewStore.showItems"
              :style="{
                position: 'absolute',
                transform: 'translate(-50%, -50%)',
                top:
                  item.transformed.y *
                    (topViewStore.topViewSize.height * topViewStore.currentSport.heightRel) +
                  ((1 - topViewStore.currentSport.heightRel) / 2) *
                    topViewStore.topViewSize.height +
                  'px',
                left:
                  item.transformed.x *
                    (topViewStore.topViewSize.width * topViewStore.currentSport.widthRel) +
                  ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width +
                  'px',
                width: '8px',
                height: '8px',
              }"
            >
              <svg
                v-if="topViewStore.currentSport.title === $t('sports.soccer.title')"
                viewBox="0 0 64 64"
              >
                <circle cx="32" cy="32" r="31" fill="#FFFFFF" />
                <path
                  d="M61.934 31.992c.021-.713.209-10.904-5.822-17.538c-.268-.593-1.539-2.983-5.641-5.904a41.959 41.959 0 0 0-5.775-3.763l-.008-.004C44.432 4.646 39.43 2 33.359 2c-.461 0-.917.027-1.368.058V2.05c-4.629-.101-9.227 1.09-11.998 2.341c-2.458 1.11-5.187 2.971-5.384 3.115C11.205 9.41 4.75 17.051 4.239 21.1c-2.063 2.637-3.787 14.482.004 21.697c2.658 10.027 12.664 15.045 13.46 15.43c.484.309 5.937 3.68 12.636 3.68c.281 0 1.98.094 2.586.094c7.241 0 17.971-5.104 20.217-9.102c6.171-4.514 9.37-16.147 8.792-20.907M17.758 47.055c-2.869-4.641-4.504-10.705-4.854-12.098c.908-1.361 5.387-7.965 7.939-9.952c1.445.266 7.479 1.374 13.17 2.404c.715 1.853 3.852 10.029 4.75 13.185c-.99 1.174-4.879 5.702-8.708 9.248c-4.065.019-10.979-2.326-12.297-2.787M53.824 14.58c-.012.45-.119 2.05-.885 3.887c-1.521-.777-5.344-2.441-10.584-2.722c-.793-1.171-3.777-5.254-8.49-8.086c.645-1.262 1.543-2.801 2.068-3.27c.17-.048.434-.092.836-.092c2.527 0 6.893 1.655 7.273 1.802c.403.213 8.251 4.439 9.782 8.481M11.773 34.012c-3.423-.584-5.458-1.648-6.066-2.008c-1.273-4.617-.248-9.607-.09-10.322c1.256-2.246 4.832-7.971 7.191-9.058c2.445-.499 5.494.121 6.736.424c-.117 1.615-.342 6.127.326 10.862c-2.706 2.178-6.989 8.447-8.097 10.102M31.685 3.53c.768.057 1.895.225 2.667.454c-.77 1.024-1.559 2.542-1.932 3.292c-1.57.257-7.533 1.397-12.211 4.43c-.943-.25-3.791-.917-6.488-.687c.668-1.293 1.666-2.249 1.773-2.347c.371-.266 7.513-5.263 16.191-5.155v.013m19.096 38.093c-1.17-.048-5.678-.305-10.621-1.466c-.947-3.302-4.074-11.444-4.789-13.296a556.586 556.586 0 0 1 6.928-9.654c5.688.312 9.682 2.387 10.455 2.82c3.295 5.299 4.018 10.711 4.117 11.615c-1.75 5.446-5.211 9.113-6.09 9.981M3.655 28.519c.084 1.266.287 2.599.654 3.917a11.738 11.738 0 0 0-.682 2.651a33.039 33.039 0 0 1 .028-6.568m9.644 23.359c1.508-1.453 3.367-2.867 4.088-3.401c1.63.574 8.324 2.837 12.591 2.837c.727.975 3.104 4.028 6.018 6.362c-1.814 1.775-4.434 2.613-4.897 2.752c-8.127.218-16.042-4.35-17.8-8.55m21.463 8.538c.922-.537 1.883-1.244 2.678-2.139c1.297-.179 6.863-1.137 11.893-4.832c.332.036.879.08 1.49.063c-3.018 2.957-10.382 6.26-16.061 6.908m15.424-8.376c1.807-4.708 1.73-8.258 1.641-9.392c.992-.972 4.396-4.599 6.285-10.113c1.018.17 1.68.429 1.994.574c.109.4.291 1.324.188 2.725c-.77 5.043-3.428 12.6-8.084 15.941c-.468.239-1.292.291-2.024.265"
                />
              </svg>

              <svg
                v-else-if="topViewStore.currentSport.title === $t('sports.handball.title')"
                viewBox="0 0 512 512"
              >
                <circle cx="256" cy="256" r="255" fill="#FFFFFF" />
                <path
                  d="M454.96,417.077c0.538-0.664,1.076-1.327,1.607-1.995c0.648-0.816,1.289-1.638,1.928-2.462
    c0.36-0.465,0.717-0.933,1.074-1.401C492.453,368.156,512,314.364,512,256C512,114.618,397.382,0,256,0S0,114.618,0,256
    c0,58.512,19.646,112.428,52.681,155.544c0.214,0.28,0.428,0.561,0.644,0.84c0.742,0.96,1.489,1.917,2.244,2.867
    c0.315,0.396,0.634,0.787,0.951,1.181c45.688,56.736,115.07,93.586,193.125,95.488c2.117,0.053,4.235,0.08,6.354,0.08
    s4.238-0.027,6.354-0.08C340.114,510.025,409.266,473.447,454.96,417.077z
    M268.597,468.953c-1.066,0.064-2.133,0.115-3.2,0.163c-0.779,0.034-1.558,0.063-2.339,0.089
    c-0.732,0.025-1.465,0.05-2.197,0.067c-1.616,0.036-3.235,0.062-4.86,0.062s-3.244-0.025-4.86-0.062
    c-0.733-0.017-1.465-0.043-2.197-0.067c-0.781-0.025-1.561-0.055-2.339-0.089c-1.067-0.048-2.134-0.099-3.2-0.163
    c-0.181-0.01-0.361-0.023-0.541-0.034c-6.992-0.437-13.97-1.219-20.925-2.343L176,405.333l48-63.999h64l48,63.999
    l-45.937,61.243c-6.955,1.124-13.932,1.905-20.925,2.343C268.958,468.93,268.778,468.943,268.597,468.953z
    M260.899,42.729c1.184,0.027,2.365,0.072,3.547,0.119c0.445,0.017,0.891,0.031,1.336,0.051c1.401,0.065,2.8,0.143,4.197,0.236
    c0.139,0.009,0.278,0.017,0.417,0.026c20.451,1.391,40.445,5.74,59.629,12.867l5.979,7.975L288.005,128h-64.006
    l-47.998-63.997l5.981-7.977c19.167-7.125,39.174-11.475,59.636-12.866c0.126-0.008,0.252-0.016,0.378-0.024
    c1.409-0.093,2.819-0.172,4.232-0.238c0.432-0.02,0.865-0.032,1.298-0.049c1.193-0.048,2.387-0.093,3.584-0.121
    c0.64-0.014,1.282-0.016,1.923-0.024c0.99-0.014,1.979-0.033,2.97-0.033c0.972,0,1.942,0.019,2.913,0.033
    C259.576,42.713,260.239,42.714,260.899,42.729z
    M224,298.667l-47.997-63.996l48-64h63.994l48,64L288,298.667H224z
    M437.337,213.335h-64.002l-47.998-63.998l47.997-63.996h10.42c34.098,25.567,59.876,60.762,73.787,101.051
    L437.337,213.335z
    M186.663,149.338l-47.997,63.996H74.661l-20.202-26.94c13.911-40.289,39.689-75.484,73.787-101.051h10.42
    L186.663,149.338z
    M74.66,256.009h64.013L186.667,320l-48,64H85.336c-19.748-26.337-33.155-57.122-39.051-90.158L74.66,256.009z
    M373.335,384.002l-48-64l47.995-63.994h64.01l28.377,37.836c-5.896,33.036-19.303,63.821-39.051,90.158H373.335z
    M138.667,426.667l10.529,14.037c-7.358-4.264-14.438-8.953-21.206-14.037H138.667z
    M373.331,426.669h10.676c-6.767,5.083-13.846,9.771-21.203,14.035L373.331,426.669z"
                />
              </svg>

              <svg
                v-else-if="topViewStore.currentSport.title === $t('sports.basketball.title')"
                id="Layer_1"
                xmlns="http://www.w3.org/2000/svg"
                xmlns:xlink="http://www.w3.org/1999/xlink"
                viewBox="0 0 64 64"
                enable-background="new 0 0 64 64"
                xml:space="preserve"
                fill="#000000"
              >
                <g id="SVGRepo_bgCarrier" stroke-width="0"></g>
                <g id="SVGRepo_tracerCarrier" stroke-linecap="round" stroke-linejoin="round"></g>
                <g id="SVGRepo_iconCarrier">
                  <g>
                    <path
                      fill="#000000"
                      d="M54.627,9.372c-12.496-12.494-32.758-12.494-45.254,0c-12.497,12.496-12.497,32.758,0,45.256 c12.496,12.496,32.758,12.496,45.254,0C67.124,42.13,67.124,21.868,54.627,9.372z M53.213,10.786 c4.428,4.428,7.179,9.895,8.261,15.615c-9.549-0.729-19.344,2.539-26.646,9.84c-1.283,1.283-2.437,2.646-3.471,4.066 c-2.487-1.861-4.873-3.926-7.136-6.188c-0.568-0.568-1.106-1.156-1.648-1.74c1.785-2.346,3.748-4.602,5.892-6.744 c7.077-7.078,15.369-12.184,24.198-15.373C52.847,10.437,53.033,10.606,53.213,10.786z M50.973,8.759 c-8.719,3.309-16.901,8.441-23.922,15.463c-2.117,2.117-4.065,4.34-5.845,6.65c-2.224-2.543-4.227-5.211-5.993-7.986 c4.333-5.684,6.633-12.416,6.904-19.217C31.742,0.319,42.732,2.015,50.973,8.759z M10.787,10.786 c2.755-2.756,5.915-4.854,9.285-6.312c-0.395,5.848-2.387,11.605-5.978,16.566c-1.728-2.922-3.208-5.945-4.448-9.047 C10.014,11.585,10.393,11.181,10.787,10.786z M8.193,13.755c1.291,3.084,2.818,6.086,4.582,8.988 c-0.625,0.75-1.285,1.482-1.988,2.186c-2.626,2.625-5.599,4.686-8.766,6.207C2.196,24.985,4.254,18.882,8.193,13.755z M2.031,33.339c3.688-1.645,7.145-3.971,10.17-6.996c0.588-0.588,1.142-1.199,1.678-1.818c1.809,2.777,3.848,5.447,6.104,7.992 c-4.463,6.176-7.752,12.934-9.889,19.967C5.03,47.075,2.34,40.253,2.031,33.339z M11.712,54.093 c2.021-7.07,5.231-13.871,9.654-20.074c0.479,0.506,0.945,1.021,1.441,1.516c2.351,2.352,4.832,4.488,7.419,6.422 c-3.73,5.818-5.498,12.527-5.329,19.193C20.114,59.989,15.563,57.634,11.712,54.093z M53.213,53.212 c-7.156,7.158-17.028,9.934-26.299,8.348c-0.253-6.389,1.382-12.836,4.933-18.424c6.625,4.654,13.896,7.979,21.445,9.994 C53.265,53.157,53.24,53.187,53.213,53.212z M32.979,41.481c0.974-1.336,2.057-2.619,3.263-3.826 c6.99-6.988,16.407-10.049,25.538-9.219c0.961,8.076-1.356,16.463-6.953,23.016C47.13,49.53,39.712,46.212,32.979,41.481z"
                    />
                    <g>
                      <path
                        fill="#bd613c"
                        d="M22.573,32.38c0.542,0.584,1.08,1.172,1.648,1.74c2.263,2.262,4.648,4.326,7.136,6.188 c1.034-1.42,2.188-2.783,3.471-4.066c7.302-7.301,17.097-10.568,26.646-9.84c-1.082-5.721-3.833-11.188-8.261-15.615 c-0.18-0.18-0.366-0.35-0.55-0.523c-8.829,3.189-17.121,8.295-24.198,15.373C26.321,27.778,24.358,30.034,22.573,32.38z"
                      />
                      <path
                        fill="#bd613c"
                        d="M21.206,30.872c1.779-2.311,3.728-4.533,5.845-6.65C34.071,17.2,42.254,12.067,50.973,8.759 c-8.24-6.744-19.23-8.439-28.855-5.09c-0.271,6.801-2.571,13.533-6.904,19.217C16.979,25.661,18.982,28.329,21.206,30.872z"
                      />
                      <path
                        fill="#bd613c"
                        d="M20.072,4.474c-3.37,1.459-6.53,3.557-9.285,6.312c-0.395,0.395-0.773,0.799-1.141,1.207 c1.24,3.102,2.721,6.125,4.448,9.047C17.686,16.079,19.678,10.321,20.072,4.474z"
                      />
                      <path
                        fill="#bd613c"
                        d="M12.775,22.743c-1.764-2.902-3.291-5.904-4.582-8.988c-3.939,5.127-5.997,11.23-6.172,17.381 c3.167-1.521,6.14-3.582,8.766-6.207C11.49,24.226,12.15,23.493,12.775,22.743z"
                      />
                      <path
                        fill="#bd613c"
                        d="M13.879,24.524c-0.536,0.619-1.09,1.23-1.678,1.818c-3.025,3.025-6.482,5.352-10.17,6.996 c0.309,6.914,2.999,13.736,8.062,19.145c2.137-7.033,5.426-13.791,9.889-19.967C17.727,29.972,15.688,27.302,13.879,24.524z"
                      />
                      <path
                        fill="#bd613c"
                        d="M22.808,35.534c-0.496-0.494-0.963-1.01-1.441-1.516c-4.423,6.203-7.633,13.004-9.654,20.074 c3.852,3.541,8.402,5.896,13.186,7.057c-0.169-6.666,1.599-13.375,5.329-19.193C27.64,40.022,25.158,37.886,22.808,35.534z"
                      />
                      <path
                        fill="#bd613c"
                        d="M26.914,61.56c9.271,1.586,19.143-1.189,26.299-8.348c0.027-0.025,0.052-0.055,0.079-0.082 c-7.549-2.016-14.82-5.34-21.445-9.994C28.296,48.724,26.661,55.171,26.914,61.56z"
                      />
                      <path
                        fill="#bd613c"
                        d="M61.78,28.437c-9.131-0.83-18.548,2.23-25.538,9.219c-1.206,1.207-2.289,2.49-3.263,3.826 c6.732,4.73,14.15,8.049,21.848,9.971C60.424,44.899,62.741,36.513,61.78,28.437z"
                      />
                    </g>
                    <path
                      opacity="0.2"
                      fill="#231F20"
                      d="M26.914,61.56c9.271,1.586,19.143-1.189,26.299-8.348c0.027-0.025,0.052-0.055,0.079-0.082 c-7.549-2.016-14.82-5.34-21.445-9.994C28.296,48.724,26.661,55.171,26.914,61.56z"
                    />
                    <path
                      opacity="0.2"
                      fill="#231F20"
                      d="M61.78,28.437c-9.131-0.83-18.548,2.23-25.538,9.219c-1.206,1.207-2.289,2.49-3.263,3.826 c6.732,4.73,14.15,8.049,21.848,9.971C60.424,44.899,62.741,36.513,61.78,28.437z"
                    />
                    <g opacity="0.2">
                      <path
                        fill="#FFFFFF"
                        d="M10.787,10.786c-0.395,0.395-0.773,0.799-1.141,1.207c1.24,3.102,2.721,6.125,4.448,9.047 c3.591-4.961,5.583-10.719,5.978-16.566C16.702,5.933,13.542,8.03,10.787,10.786z"
                      />
                      <path
                        fill="#FFFFFF"
                        d="M2.021,31.136c3.167-1.521,6.14-3.582,8.766-6.207c0.703-0.703,1.363-1.436,1.988-2.186 c-1.764-2.902-3.291-5.904-4.582-8.988C4.254,18.882,2.196,24.985,2.021,31.136z"
                      />
                    </g>
                  </g>
                </g>
              </svg>
            </div>
          </template>
        </div>
      </div>
    </v-row>

    <v-row
      ref="videoControl"
      class="video-control mt-6 mb-n2 justify-center"
      data-tour="position-data-edit-row"
    >
      <v-btn :disabled="playerStore.isSynced" @click="toggleTopView" size="small">
        <v-icon v-if="topViewEnded">mdi-restart</v-icon>
        <v-icon v-else-if="topViewPlaying">mdi-pause</v-icon>
        <v-icon v-else>mdi-play</v-icon>
      </v-btn>

      <v-menu location="top">
        <template #activator="{ props }">
          <v-btn v-bind="props" size="small">
            {{ topViewStore.currentSport.title }}
          </v-btn>
        </template>
        <v-list class="py-0" density="compact" width="115px">
          <v-menu location="end" open-on-hover v-for="sport in topViewStore.sports" :key="sport">
            <template #activator="{ props }">
              <v-list-item v-bind="props" class="menu-item">
                <v-list-item-title class="d-flex justify-space-between">
                  {{ sport.title }}
                  <tab-window-icon>mdi-chevron-right</tab-window-icon>
                </v-list-item-title>
              </v-list-item>
            </template>
            <v-list class="py-0" density="compact">
              <v-list-item
                v-for="(areaData, areaSize) in sport.areas"
                :key="areaSize"
                class="menu-item"
                @click="topViewStore.onSportChange(sport.title, areaSize)"
              >
                <v-list-item-title class="my-0">
                  {{ areaData.title }}
                </v-list-item-title>
              </v-list-item>
            </v-list>
          </v-menu>
        </v-list>
      </v-menu>

      <v-menu location="top">
        <template #activator="{ props }">
          <v-btn v-bind="props" size="small">
            {{ $t("position_data.display_settings.title") }}
          </v-btn>
        </template>
        <v-list class="py-0" density="compact" width="225px">
          <v-list-item
            class="menu-item"
            @click="bboxesStore.viewBoundingBox"
            :disabled="
              !bboxesStore.bboxDataActive || Object.keys(bboxesStore.bboxDataActive).length === 0
            "
          >
            <v-list-item-title class="d-flex justify-space-between">
              {{ $t("position_data.display_settings.view_bounding_box") }}
              <tab-window-icon
                :class="{
                  'text-disabled':
                    !bboxesStore.showBoundingBox ||
                    !bboxesStore.bboxDataActive ||
                    Object.keys(bboxesStore.bboxDataActive).length === 0,
                  'text-red': bboxesStore.showBoundingBox,
                }"
              >
                mdi-check
              </tab-window-icon>
            </v-list-item-title>
          </v-list-item>

          <v-list-item class="menu-item" @click="topViewStore.viewPlayerId">
            <v-list-item-title class="d-flex justify-space-between">
              {{ $t("position_data.display_settings.view_player_id") }}
              <tab-window-icon
                :class="{
                  'text-disabled': !topViewStore.showPlayerId,
                  'text-red': topViewStore.showPlayerId,
                }"
              >
                mdi-check
              </tab-window-icon>
            </v-list-item-title>
          </v-list-item>

          <v-list-item class="menu-item" @click="playerStore.toggleSliderSync">
            <v-list-item-title class="d-flex justify-space-between">
              {{ $t("position_data.display_settings.video_sync") }}
              <tab-window-icon
                :class="{
                  'text-disabled': !playerStore.isSynced,
                  'text-red': playerStore.isSynced,
                }"
              >
                mdi-check
              </tab-window-icon>
            </v-list-item-title>
          </v-list-item>

          <v-list-item class="menu-item" @click="showModalPositionDataTeamColors = true">
            <v-list-item-title class="d-flex justify-space-between">
              {{ $t("position_data.display_settings.team_colors") }}
            </v-list-item-title>
          </v-list-item>

          <v-list-item class="menu-item" @click="showModalPositionDataOffset = true">
            <v-list-item-title class="d-flex justify-space-between">
              {{ $t("position_data.display_settings.offset") }}
            </v-list-item-title>
          </v-list-item>

          <v-menu location="end" open-on-hover>
            <template #activator="{ props }">
              <v-list-item v-bind="props" class="menu-item">
                <v-list-item-title class="d-flex justify-space-between">
                  {{ $t("position_data.display_settings.view_kpis.title") }}
                  <tab-window-icon>mdi-chevron-right</tab-window-icon>
                </v-list-item-title>
              </v-list-item>
            </template>
            <v-list class="py-0" density="compact" width="180px">
              <v-list-item class="menu-item" @click="topViewStore.viewSpaceControl">
                <v-list-item-title class="d-flex justify-space-between">
                  {{ $t("position_data.display_settings.view_kpis.space_control") }}
                  <tab-window-icon
                    :class="{
                      'text-disabled': !topViewStore.showSpaceControl,
                      'text-red': topViewStore.showSpaceControl,
                    }"
                  >
                    mdi-check
                  </tab-window-icon>
                </v-list-item-title>
              </v-list-item>
              <v-list-item class="menu-item" @click="topViewStore.viewEffectivePlayingSpace">
                <v-list-item-title class="d-flex justify-space-between">
                  {{ $t("position_data.display_settings.view_kpis.eps") }}
                  <tab-window-icon
                    :class="{
                      'text-disabled': !topViewStore.showEffectivePlayingSpace,
                      'text-red': topViewStore.showEffectivePlayingSpace,
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
                  {{ $t("position_data.display_settings.position_data.title") }}
                  <tab-window-icon>mdi-chevron-right</tab-window-icon>
                </v-list-item-title>
              </v-list-item>
            </template>
            <v-list class="py-0" density="compact">
              <v-list-item class="menu-item" @click="showModalPositionDataUpload = true">
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
      <ModalPositionDataTeamColors
        v-if="showModalPositionDataTeamColors"
        v-model="showModalPositionDataTeamColors"
      />
      <ModalPositionDataOffset
        v-if="showModalPositionDataOffset"
        v-model="showModalPositionDataOffset"
      />

      <div class="time-code ml-2">
        {{ getTimecode(currentTime) }}
      </div>

      <v-tooltip
        v-if="topViewStore.metaDataTopView.interp_err > 0"
        class="fps-tooltip"
        :text="
          $t('position_data.fps_deviation', {
            interpErr: topViewStore.metaDataTopView.interp_err.toFixed(1),
          })
        "
      >
        <template #activator="{ props }">
          <v-icon v-bind="props" color="warning" size="small" class="ml-2 mt-1"
            >mdi-information-outline</v-icon
          >
        </template>
      </v-tooltip>
    </v-row>

    <v-row ref="videoSlider">
      <v-slider
        v-model="currentTime"
        @update:model-value="onProgressChange"
        hide-details
        color="primary"
        :disabled="playerStore.isSynced"
        :thumb-size="15"
        :step="1000 / playerStore.videoFPS"
        min="0"
        :max="playerStore.videoDuration"
      />
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from "vue";
import { usePlayerStore } from "@/stores/player";
import { useTopViewStore } from "@/stores/top_view";
import { useVideoStore } from "@/stores/video";
import { useVisualizationStore } from "@/stores/visualization";
import { useBboxesStore } from "@/stores/bboxes";
import { getTimecode } from "@/plugins/time";
import { Delaunay } from "d3-delaunay";
import PositionDataMenu from "@/components/position-data/PositionDataMenu.vue";
import ModalPositionDataSelect from "@/components/position-data/ModalPositionDataSelect.vue";
import ModalPositionDataUpload from "@/components/position-data/ModalPositionDataUpload.vue";
import ModalPositionDataTeamColors from "@/components/position-data/ModalPositionDataTeamColors.vue";
import ModalPositionDataOffset from "@/components/position-data/ModalPositionDataOffset.vue";

const playerStore = usePlayerStore();
const topViewStore = useTopViewStore();
const videoStore = useVideoStore();
const visualizationStore = useVisualizationStore();
const bboxesStore = useBboxesStore();

const showModalPositionDataSelect = ref(false);
const showModalPositionDataUpload = ref(false);
const showModalPositionDataTeamColors = ref(false);
const showModalPositionDataOffset = ref(false);

const progress = ref(0);
watch(
  () => topViewStore.currentTime,
  (newTime) => {
    progress.value = newTime;
  }
);
watch(
  () => progress.value,
  (newTime) => {
    topViewStore.currentTime = Math.round(newTime);
  }
);
const currentTime = computed({
  get() {
    return playerStore.isSynced ? playerStore.currentTime : progress.value;
  },
  set(val) {
    if (!playerStore.isSynced) {
      progress.value = Math.round(val);
      topViewStore.currentTime = Math.round(val);
    }
  },
});
const onProgressChange = (time) => {
  if (!playerStore.isSynced) {
    progress.value = Math.round(time);
    topViewStore.currentTime = Math.round(time);
  }
};
watch(
  () => playerStore.isSynced,
  (isSynced) => {
    if (!isSynced) {
      progress.value = playerStore.currentTime;
    }
  }
);

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

const includedPlayers = ref(new Set());
watch(
  () => topViewStore.positionDataTopView,
  (newVal) => {
    const all = Object.values(newVal)
      .flat()
      .filter((p) => p[1] !== 1);

    includedPlayers.value = new Set(all.map((p) => p[0]));
  },
  { immediate: true, deep: true }
);
const togglePlayersForKPIs = (playerId) => {
  const newSet = new Set(includedPlayers.value);
  if (newSet.has(playerId)) {
    newSet.delete(playerId);
  } else {
    newSet.add(playerId);
  }
  includedPlayers.value = newSet;
};

const transformCoordinateToCrop = (x, y, cropPct) => {
  if (!cropPct) return { x, y };

  const xRange = cropPct.x;
  const yRange = cropPct.y;

  const xCrop = (x - xRange[0]) / (xRange[1] - xRange[0]);
  const yCrop = (y - yRange[0]) / (yRange[1] - yRange[0]);

  return { x: xCrop, y: yCrop };
};

const computeConvexHull = (points) => {
  if (points.length < 3) return [];
  const sortedPoints = points.slice().sort((a, b) => a.left - b.left || a.top - b.top);

  const cross = (o, a, b) =>
    (a.left - o.left) * (b.top - o.top) - (a.top - o.top) * (b.left - o.left);

  const lower = [];
  for (const p of sortedPoints) {
    while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], p) <= 0) {
      lower.pop();
    }
    lower.push(p);
  }

  const upper = [];
  for (let i = sortedPoints.length - 1; i >= 0; i--) {
    const p = sortedPoints[i];
    while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], p) <= 0) {
      upper.pop();
    }
    upper.push(p);
  }

  lower.pop();
  upper.pop();

  return lower.concat(upper);
};
const convexHullPlayer = computed(() => {
  if (!topViewStore.topViewSize || !topViewStore.positionDataTopView) {
    return {};
  }

  const cropPct = topViewStore.currentSport.areas?.[topViewStore.currentAreaSize]?.templateCrop;

  const result = {};
  Object.entries(topViewStore.positionDataTopView).forEach(([timeKey, framePositions]) => {
    const teams = {};
    framePositions
      .filter((position) => position[1] !== 1 && includedPlayers.value.has(position[0]))
      .forEach((position) => {
        const transformed = transformCoordinateToCrop(position[3], position[4], cropPct);

        const top =
          transformed.y * topViewStore.topViewSize.height * topViewStore.currentSport.heightRel +
          ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height;
        const left =
          transformed.x * topViewStore.topViewSize.width * topViewStore.currentSport.widthRel +
          ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width;
        if (!teams[position[1]]) {
          teams[position[1]] = [];
        }
        teams[position[1]].push({ left, top });
      });
    const hulls = {};
    Object.keys(teams).forEach((team) => {
      const points = teams[team];
      hulls[team] = points.length >= 3 ? computeConvexHull(points) : points;
    });
    result[timeKey] = hulls;
  });
  return result;
});

const computeVoronoi = (players) => {
  if (!players.length) return [];

  const delaunay = Delaunay.from(players.map((p) => [p.left, p.top]));
  const voronoi = delaunay.voronoi([
    ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width,

    ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height,

    ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width +
      topViewStore.topViewSize.width * topViewStore.currentSport.widthRel,

    ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height +
      topViewStore.topViewSize.height * topViewStore.currentSport.heightRel,
  ]);

  return players
    .map((player, i) => {
      const polygon = voronoi.cellPolygon(i);
      return polygon ? { team_id: player.team_id, polygon } : null;
    })
    .filter((cell) => cell !== null);
};
const voronoiCells = computed(() => {
  if (!topViewStore.topViewSize || !topViewStore.positionDataTopView) {
    return {};
  }

  const cropPct = topViewStore.currentSport.areas?.[topViewStore.currentAreaSize]?.templateCrop || {
    x: [0, 1],
    y: [0, 1],
  };

  const result = {};
  Object.entries(topViewStore.positionDataTopView).forEach(([timeKey, framePositions]) => {
    const allPlayers = framePositions
      .filter((player) => player[1] !== 1 && includedPlayers.value.has(player[0]))
      .map((player) => {
        const transformed = transformCoordinateToCrop(player[3], player[4], cropPct);

        const top =
          transformed.y * topViewStore.topViewSize.height * topViewStore.currentSport.heightRel +
          ((1 - topViewStore.currentSport.heightRel) / 2) * topViewStore.topViewSize.height;
        const left =
          transformed.x * topViewStore.topViewSize.width * topViewStore.currentSport.widthRel +
          ((1 - topViewStore.currentSport.widthRel) / 2) * topViewStore.topViewSize.width;
        return { left, top, team_id: player[1] };
      });
    result[timeKey] = computeVoronoi(allPlayers);
  });
  return result;
});

const positionDataTransformed = computed(() => {
  if (!topViewStore.positionDataTopView) return {};

  const cropPct = topViewStore.currentSport.areas?.[topViewStore.currentAreaSize]?.templateCrop || {
    x: [0, 1],
    y: [0, 1],
  };

  const result = {};
  Object.entries(topViewStore.positionDataTopView).forEach(([timeKey, framePositions]) => {
    result[timeKey] = framePositions.map((position) => {
      const transformed = transformCoordinateToCrop(position[3], position[4], cropPct);
      return {
        original: position,
        transformed: transformed,
      };
    });
  });
  return result;
});

const matchupTeams = computed(() => {
  const meta = topViewStore.metaDataTopView;
  if (!meta?.team_ids) return [];
  return Object.entries(meta.team_ids)
    .filter(([teamId]) => Number(teamId) !== 1)
    .sort(([a], [b]) => Number(a) - Number(b))
    .map(([teamId, info]) => ({
      id: Number(teamId),
      name: info.name,
      color: visualizationStore.getTeamColor(Number(teamId)),
    }));
});

const getPlayerNumber = (playerId) => {
  const meta = topViewStore.metaDataTopView;
  const num = meta?.player_ids?.[playerId]?.number;
  return num != null ? num : playerId;
};

const maxVideoHeight = ref(0);
const videoSlider = ref(null);
const videoControl = ref(null);
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
watch(() => window.innerHeight, updateMaxHeight);
watch(videoControl || videoSlider, (newVal) => {
  if (newVal) {
    nextTick(() => updateMaxHeight());
  }
});

const topViewEnded = ref(false);
const topViewPlaying = ref(false);
const toggleTopView = () => {
  if (topViewEnded.value) {
    progress.value = 0;
    topViewEnded.value = false;
    topViewPlaying.value = true;
    startTimer();
  } else if (topViewPlaying.value) {
    topViewPlaying.value = false;
    stopTimer();
  } else {
    topViewPlaying.value = true;
    startTimer();
  }
};
let topViewTimer = null;
const startTimer = () => {
  stopTimer();
  const frameInterval = 1000 / playerStore.videoFPS;
  const intervalMs = Math.max(1, Math.round(frameInterval));

  topViewTimer = setInterval(() => {
    const next = progress.value + frameInterval;
    const closestFrame = Math.round(next / frameInterval) * frameInterval;
    progress.value = Math.round(closestFrame);

    if (progress.value >= playerStore.videoDuration) {
      progress.value = playerStore.videoDuration;
      topViewEnded.value = true;
      topViewPlaying.value = false;
      stopTimer();
    }
  }, intervalMs);
};
const stopTimer = () => {
  if (topViewTimer) {
    clearInterval(topViewTimer);
    topViewTimer = null;
  }
};

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
  () => topViewStore.positionDataTopView,
  (newd) => {
    console.log("Position data updated:", newd);
  },
  { immediate: true }
);
watch(
  () => topViewStore.metaDataTopView,
  (newd) => {
    console.log("meta data updated:", newd);
  },
  { immediate: true }
);
</script>

<style scoped>
.visualizer-image {
  display: block;
  max-width: 100%;
  max-height: 100%;
}

.video-control {
  gap: 5px;
}

.video-control > .time-code {
  margin-top: auto;
  margin-bottom: auto;
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

.fps-tooltip ::v-deep(.v-overlay__content) {
  background-color: rgb(var(--v-theme-primary));
}

.position-data-player-id {
  position: absolute;
  left: 50%;
  bottom: -16px;
  transform: translateX(-50%);
  font-size: 0.8rem;
  pointer-events: none;
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

.matchup-overlay {
  position: absolute;
  top: 6px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 12px;
  z-index: 10;
  pointer-events: none;
  background: rgba(245, 245, 245, 0.88);
  backdrop-filter: blur(4px);
  border-radius: 6px;
  padding: 5px 14px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.15);
  border: 1px solid rgba(0, 0, 0, 0.08);
}

.matchup-team {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.matchup-team-name {
  color: black;
  font-size: 0.85rem;
  font-weight: 600;
  white-space: nowrap;
}

.matchup-team-line {
  display: block;
  width: 100%;
  height: 3px;
  border-radius: 1px;
}

.matchup-separator {
  color: black;
  font-size: 1rem;
  font-weight: 700;
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
</style>
