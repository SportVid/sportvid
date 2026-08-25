<template>
  <TranscriptDataMenu
    v-if="!hasTranscriptData"
    :title="$t('analysis_view.visualization_tabs.transcript')"
    icon="mdi-closed-caption-outline"
  />

  <div
    v-else
    class="d-flex flex-column flex-nowrap pa-4"
    :class="{ 'transcript-fill-height': dense }"
  >
    <div class="card-header-zone">
      <!-- Same mdi-menu -> dropdown pattern as the other tab windows (see TabWindowEvents.vue/
           TabWindowHeatmap.vue's own display-settings menu) -- transcript only has the one
           setting worth surfacing here (which whisper run to view), so the menu is a single
           item rather than a submenu tree. -->
      <v-menu location="bottom">
        <template #activator="{ props }">
          <v-btn v-bind="props" size="small" class="mt-0 mr-1">
            <v-icon>mdi-menu</v-icon>
          </v-btn>
        </template>
        <v-list class="py-0" density="compact" width="160px">
          <!-- Drops just the current selection (demo flag + selectedTranscriptRunId) so this
               card falls back to its own TranscriptDataMenu -- lets the user generate a new
               whisper run or pick a different one right here instead of having to go back to
               VideoView and reopen the video just to get back to that empty state. -->
          <v-list-item
            v-if="canWrite"
            class="menu-item"
            @click="
              timelineSegmentAnnotationStore.resetDemoTranscript();
              timelineSegmentAnnotationStore.resetTranscriptSelection();
            "
          >
            <v-list-item-title>{{ $t("transcript_data.create_new") }}</v-list-item-title>
          </v-list-item>
          <v-list-item class="menu-item" @click="showModalTranscriptSelect = true">
            <v-list-item-title>{{ $t("transcript_data.select") }}</v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>
      <ModalTranscriptSelect v-if="showModalTranscriptSelect" v-model="showModalTranscriptSelect" />

      <v-text-field
        v-if="viewMode === 'list'"
        v-model="search"
        append-inner-icon="mdi-magnify"
        :label="$t('visualization.transcript.search')"
        density="compact"
        single-line
        hide-details
        clearable
        class="transcript-header-control"
      />
      <v-select
        v-else
        v-model="stopwordSelection"
        :items="stopwordOptions"
        :label="$t('visualization.wordcloud.stopwords_label')"
        density="compact"
        hide-details
        multiple
        class="transcript-header-control"
      />

      <!-- Both views are the same underlying transcript, just read two different ways --
           one card with a switch, not two separate cards, so "Transcript" only occupies one
           slot in the tab group (see dashboardWidgets.js). -->
      <v-btn-toggle v-model="viewMode" mandatory density="compact" class="transcript-view-toggle">
        <v-btn value="list" :title="$t('visualization.transcript.view_list')" size="small">
          <v-icon>mdi-view-sequential-outline</v-icon>
        </v-btn>
        <v-btn
          value="wordcloud"
          :title="$t('visualization.transcript.view_wordcloud')"
          size="small"
        >
          <v-icon>mdi-cloud-outline</v-icon>
        </v-btn>
      </v-btn-toggle>
    </div>

    <!-- v-show (not v-if) for both views -- keeps the wordcloud's container ref and its
         ResizeObserver alive while the list is showing, and vice versa, so switching back
         doesn't need to re-measure/re-layout from scratch. -->
    <div v-show="viewMode === 'list'" ref="wrapperRef" class="transcript-list">
      <div v-if="filteredTranscripts.length === 0" class="transcript-empty-search">
        {{ $t("visualization.transcript.no_results") }}
      </div>
      <TranscriptListItem
        v-for="item in filteredTranscripts"
        :key="item.id"
        :ref="(el) => setItemRef(el, item.id)"
        :transcript="item"
        @highlighted="onHighlighted"
        class="mt-2"
      />
    </div>

    <div v-show="viewMode === 'wordcloud'" class="wordcloud-canvas-wrap">
      <div v-if="noWordsAvailable" class="wordcloud-empty">
        {{ $t("visualization.wordcloud.no_words") }}
      </div>
      <div ref="wordcloudContainer" class="wordcloud-canvas"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onBeforeUnmount, nextTick } from "vue";
import { useI18n } from "vue-i18n";
import { debounce } from "lodash";
import * as d3 from "d3";
import cloud from "d3-cloud";
import { removeStopwords, deu, eng } from "stopword";
import { useTimelineSegmentAnnotationStore } from "@/stores/timeline_segment_annotation";
import { usePlayerStore } from "@/stores/player";
import { useUserStore } from "@/stores/user";
import TranscriptDataMenu from "@/components/transcript/TranscriptDataMenu.vue";
import TranscriptListItem from "@/components/transcript/TranscriptListItem.vue";
import ModalTranscriptSelect from "@/components/transcript/ModalTranscriptSelect.vue";

defineProps({
  // True when this widget's height is capped to share a row with another widget (see
  // DashboardCell's `constrained`) -- makes the active view claim the rest of the column's
  // height instead of stopping at its own content-based size. Same convention as
  // TabWindowEvents.vue's `dense`.
  dense: { type: Boolean, default: false },
});

const { t } = useI18n();
const timelineSegmentAnnotationStore = useTimelineSegmentAnnotationStore();
const playerStore = usePlayerStore();
const userStore = useUserStore();

const hasTranscriptData = computed(
  () => timelineSegmentAnnotationStore.transcriptSegments.length > 0
);

const canWrite = computed(() => {
  if (userStore.role === "admin") return true;
  const ownerUsername = playerStore.video?.owner_username;
  if (!ownerUsername) return true;
  return ownerUsername === userStore.username;
});

const viewMode = ref("list");
const showModalTranscriptSelect = ref(false);

// ---------------------------------------------------------------------------
// List view: live transcript, auto-scrolling to whatever's currently being spoken.
// ---------------------------------------------------------------------------

const search = ref("");

const filteredTranscripts = computed(() => {
  const query = search.value?.toLowerCase().trim() ?? "";
  const segments = timelineSegmentAnnotationStore.transcriptSegments;
  if (!query) return segments;
  return segments.filter((t) => t.name.toLowerCase().includes(query));
});

// Keeps the segment currently being spoken scrolled into view as playback advances -- the
// same "table keeps running along" treatment as EventsList.vue's scrollToNext, just centered
// on the active row instead of pinned under the header (a transcript has no header row to
// pin under).
const wrapperRef = ref(null);
const itemRefs = ref({});
const setItemRef = (el, id) => {
  if (el) itemRefs.value[id] = el.$el ?? el;
  else delete itemRefs.value[id];
};

const scrollToCurrent = debounce((id) => {
  if (!playerStore.syncTime) return;
  const el = itemRefs.value[id];
  const wrapper = wrapperRef.value;
  if (!el || !wrapper) return;
  // Deliberately not el.scrollIntoView(): it walks every scrollable ancestor (this wrapper,
  // but also the dashboard cell/page around it) and aligns the row to each one's own top/
  // center, so the whole page would scroll along with the list. Scrolling just this
  // wrapper's scrollTop keeps the effect contained to the list itself.
  const wrapperRect = wrapper.getBoundingClientRect();
  const elRect = el.getBoundingClientRect();
  const targetScrollTop =
    wrapper.scrollTop +
    (elRect.top - wrapperRect.top) -
    wrapper.clientHeight / 2 +
    elRect.height / 2;
  wrapper.scrollTo({ top: targetScrollTop, behavior: "smooth" });
}, 150);

const onHighlighted = (id) => nextTick(() => scrollToCurrent(id));

// ---------------------------------------------------------------------------
// Wordcloud view: static word frequency, same transcript text.
// ---------------------------------------------------------------------------

const stopwordOptions = [
  { title: t("visualization.wordcloud.stopwords_english"), value: "en" },
  { title: t("visualization.wordcloud.stopwords_german"), value: "de" },
];
// Default: no stopwords removed. "" is not a real option -- an empty array (nothing
// selected) is what actually renders as an empty v-select, without a bogus "" chip
// alongside a real one once the user picks a language.
const stopwordSelection = ref([]);

const CUSTOM_FILTER = new Set(["", "..", ".", "?", "!"]);
const NUM_WORDS = 40;
// Tune these to change how big the most-/least-frequent word in the cloud can render.
const MIN_FONT_SIZE = 14;
const MAX_FONT_SIZE = 90;
// Inset (px) the word layout keeps from the canvas edge on every side -- see renderWordCloud.
const LAYOUT_MARGIN = 24;

// Word counts only depend on the transcript text + selected stopword languages, not on the
// container size -- kept separate from the d3-cloud layout step below so a resize alone
// doesn't need to re-tally words, and so `noWordsAvailable` (all words filtered out, e.g. a
// short transcript with only stopwords) can be read directly off this.
const wordCounts = computed(() => {
  const allWords = [];
  for (const transcript of timelineSegmentAnnotationStore.transcriptSegments) {
    for (let word of transcript.name.split(" ")) {
      if (word.endsWith(",") || word.endsWith(".")) word = word.slice(0, -1);
      allWords.push(word.toLowerCase());
    }
  }

  let filtered = allWords;
  if (stopwordSelection.value.includes("en")) filtered = removeStopwords(filtered, eng);
  if (stopwordSelection.value.includes("de")) filtered = removeStopwords(filtered, deu);

  const counts = {};
  for (const word of filtered) {
    if (CUSTOM_FILTER.has(word)) continue;
    counts[word] = (counts[word] || 0) + 1;
  }

  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, NUM_WORDS)
    .map(([text, count]) => ({ text, count }));
});

const noWordsAvailable = computed(() => wordCounts.value.length === 0);

const wordcloudContainer = ref(null);

function drawWordCloud(words) {
  const el = wordcloudContainer.value;
  if (!el) return;
  const width = el.clientWidth;
  const height = el.clientHeight;

  d3.select(el).select("svg").remove();

  const colorScale = d3.scaleOrdinal(d3.schemeTableau10);
  d3.select(el)
    .append("svg")
    .attr("width", width)
    .attr("height", height)
    .append("g")
    .attr("transform", `translate(${width / 2},${height / 2})`)
    .selectAll("text")
    .data(words)
    .enter()
    .append("text")
    .style("font-family", "Arial")
    .style("font-size", (d) => `${d.size}px`)
    .style("fill", (d, i) => colorScale(i))
    .attr("text-anchor", "middle")
    .attr("transform", (d) => `translate(${[d.x, d.y]})rotate(${d.rotate})`)
    .text((d) => d.text);
}

function renderWordCloud() {
  const el = wordcloudContainer.value;
  // clientWidth/Height are 0 while the wordcloud view is hidden behind v-show (display:
  // none) -- bail rather than lay out into a zero-size box; switching back to this view
  // fires the resize observer below (0x0 -> real size counts as a resize) and re-renders.
  if (!el || el.clientWidth === 0 || el.clientHeight === 0) return;

  const words = wordCounts.value;
  if (words.length === 0) {
    d3.select(el).select("svg").remove();
    return;
  }

  // Map counts onto font sizes between MIN_FONT_SIZE and MAX_FONT_SIZE -- without a floor, a
  // transcript with a big gap between its most- and least-frequent word (e.g. top word said
  // 50 times, others once) would size the rarest words down to a few illegible pixels.
  const max = words[0].count;
  const sized = words.map((w) => ({
    ...w,
    count: MIN_FONT_SIZE + (w.count / max) * (MAX_FONT_SIZE - MIN_FONT_SIZE),
  }));

  // Lay words out into a box inset from the actual canvas by LAYOUT_MARGIN on every side --
  // d3-cloud only keeps a word's *center* inside `size`, so a word placed near the edge can
  // still have half its glyphs stick out past the box and get clipped by the SVG's own
  // bounds (the canvas below is exactly el.clientWidth/Height). The margin gives every word
  // room to fully fit inside the visible canvas instead of running off the corners.
  const layoutWidth = Math.max(el.clientWidth - LAYOUT_MARGIN * 2, 50);
  const layoutHeight = Math.max(el.clientHeight - LAYOUT_MARGIN * 2, 50);

  cloud()
    .size([layoutWidth, layoutHeight])
    .words(sized)
    .padding(8)
    .rotate(() => 0)
    .fontSize((d) => d.count)
    .on("end", drawWordCloud)
    .start();
}

const scheduleRender = () => nextTick(renderWordCloud);

// Re-lay-out on container resize (dashboard cells resize with the window and with layout
// edits, and switching into this view from the list view counts as one too) as well as
// whenever the word list itself changes.
const resizeObserver = new ResizeObserver(() => scheduleRender());

watch(
  wordcloudContainer,
  (el, oldEl) => {
    if (oldEl) resizeObserver.unobserve(oldEl);
    if (el) {
      resizeObserver.observe(el);
      scheduleRender();
    }
  },
  { immediate: true }
);

watch(wordCounts, scheduleRender);

onBeforeUnmount(() => resizeObserver.disconnect());
</script>

<style scoped>
.card-header-zone {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.transcript-header-control {
  flex: 1 1 auto;
  max-width: 450px;
}

.transcript-view-toggle {
  flex-shrink: 0;
  margin-left: auto;
}

/* Matches the other tab windows' own .menu-item styling (see TabWindowEvents.vue/
   TabWindowHeatmap.vue). */
.menu-item {
  cursor: pointer;
}
.menu-item:hover {
  background-color: #f0f0f0;
}
.menu-item .v-list-item-title {
  font-size: 12px;
}

.transcript-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow-y: auto;
}

.transcript-empty-search {
  padding: 24px 12px;
  text-align: center;
  color: rgba(var(--v-theme-on-surface), 0.6);
}

.wordcloud-canvas-wrap {
  position: relative;
  flex: 1 1 auto;
  min-height: 400px;
}

.wordcloud-canvas,
.wordcloud-empty {
  position: absolute;
  inset: 0;
}

/* Browsers clip an <svg> to its own width/height by default -- on top of the
   LAYOUT_MARGIN inset (see renderWordCloud), this is the safety net for a large word whose
   glyphs still poke past that margin: it spills into the surrounding padding instead of
   getting a hard cut edge. */
.wordcloud-canvas :deep(svg) {
  overflow: visible;
}

.wordcloud-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(var(--v-theme-on-surface), 0.6);
  text-align: center;
}

/* dense (see `dense` prop): fills the rest of the column's height instead of stopping at its
   own content-based size -- min-height: 0 is what lets a flex child shrink below its
   content's natural size, so the list's own overflow-y: auto actually kicks in and the
   wordcloud loses its fixed floor in favor of the available space. */
.transcript-fill-height {
  height: 100%;
  min-height: 0;
}

.transcript-fill-height .transcript-list,
.transcript-fill-height .wordcloud-canvas-wrap {
  min-height: 0;
}
</style>
