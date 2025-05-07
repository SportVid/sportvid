<template>
  <v-card :class="['d-flex', 'flex-column', 'pa-2', 'ma-4']" elevation="4" :loading="loading">
    <v-row no-gutters align="center" class="px-2 py-0">
      <v-col cols="3">
        <v-list-item-content min-width>
          <div style="font-size: 16px">
            {{ cluster.name }}
            <v-dialog v-model="show" max-width="1000">
              <template #activator="{ props }">
                <v-btn v-bind="props" @click="show = true" icon size="16">
                  <v-icon>mdi-pencil</v-icon>
                </v-btn>
              </template>

              <v-card>
                <v-card-title class="mb-2">
                  {{ $t("modal.timeline.rename.title") }}
                  <v-btn icon @click="show = false" absolute top right>
                    <v-icon>mdi-close</v-icon>
                  </v-btn>
                </v-card-title>
                <v-card-text>
                  <v-text-field
                    ref="rename_input"
                    :label="$t('modal.timeline.rename.name')"
                    prepend-icon="mdi-pencil"
                    v-model="renameValue"
                  ></v-text-field>
                </v-card-text>
                <v-card-actions class="pt-0">
                  <v-btn class="mr-4" @click="renameCluster" :disabled="renaming || !cluster.name">
                    {{ $t("modal.timeline.rename.update") }}
                  </v-btn>
                  <v-btn @click="show = false">{{ $t("modal.timeline.rename.close") }}</v-btn>
                </v-card-actions>
              </v-card>
            </v-dialog>
          </div>
          <v-list-item-subtitle>{{ type_name }}s: {{ cluster.items.length }}</v-list-item-subtitle>
          <v-list-item-subtitle>First occurence: {{ firstOccurence }}</v-list-item-subtitle>
          <v-list-item-subtitle>Last occurence: {{ lastOccurence }}</v-list-item-subtitle>
        </v-list-item-content>
      </v-col>

      <v-col cols="8" style="width: 100%">
        <div
          class="image-container"
          style="
            width: 100%;
            gap: 10px;
            overflow-x: auto;
            justify-content: flex-start;
            display: flex;
            flex-direction: row;
          "
        >
          <v-img
            v-for="thumb in thumbnails"
            :key="thumb.id"
            :src="thumb.image_path"
            contain
            style="cursor: pointer; height: 100px; max-width: 100px"
            @click="goToFace(thumb.time)"
          ></v-img>
        </div>
      </v-col>

      <v-col align="end" cols="1">
        <v-menu v-model="showDotMenu" bottom right>
          <template #activator="{ on, attrs }">
            <v-btn icon small>
              <v-icon v-bind="attrs" v-on="on">mdi-dots-vertical</v-icon>
            </v-btn>
          </template>
          <v-list>
            <v-list-item>
              <ClusterExploration
                :cluster="cluster"
                :allClusters="allClusters"
                @deleteCluster="deleteCluster"
              ></ClusterExploration>
            </v-list-item>
            <v-list-item>
              <v-btn text @click="createTimeline">
                <v-icon left>{{ "mdi-barcode" }}</v-icon>
                {{ $t("button.to_timeline") }}
              </v-btn>
            </v-list-item>
            <v-list-item>
              <v-btn text @click="deleteCluster">
                <v-icon left>{{ "mdi-trash-can-outline" }}</v-icon
                >{{ $t("button.delete") }}
              </v-btn>
            </v-list-item>
            <v-list-item>
              <v-dialog v-model="mergeDialog" width="500" :scrollable="false">
                <template #activator="{ on, attrs }">
                  <v-btn :disabled="mergableClusters.length == 0" text v-bind="attrs" v-on="on">
                    <v-icon left>{{ "mdi-merge" }}</v-icon>
                    Merge Cluster
                  </v-btn>
                </template>
                <v-card style="max-height: 80vh; overflow-y: auto">
                  <v-card-title class="text-h5 grey lighten-2">
                    You can merge this cluster with one of the other clusters. Select one below:
                  </v-card-title>
                  <v-card-text>
                    <v-list dense>
                      <v-subheader>Clusters</v-subheader>
                      <v-list-item-group v-model="toMergeCluster" color="primary">
                        <v-list-item v-for="cluster in mergableClusters" :key="cluster.id">
                          <v-list-item-content>
                            <v-list-item-title>{{ cluster.name }}</v-list-item-title>
                          </v-list-item-content>
                        </v-list-item>
                      </v-list-item-group>
                    </v-list>
                  </v-card-text>
                  <v-divider></v-divider>
                  <v-card-actions>
                    <v-btn color="primary" text @click="cancelMergeClusters">Cancel</v-btn>
                    <v-spacer></v-spacer>
                    <v-btn
                      color="primary"
                      text
                      :disabled="toMergeCluster === undefined"
                      @click="mergeClusters"
                      >Merge</v-btn
                    >
                  </v-card-actions>
                </v-card>
              </v-dialog>
            </v-list-item>
          </v-list>
        </v-menu>
      </v-col>
    </v-row>
  </v-card>
</template>

<script>
import { ref, computed, onMounted } from "vue";
import { usePlayerStore } from "@/stores/player";
import { useClusterTimelineItemStore } from "@/stores/cluster_timeline_item";
import { usePluginRunStore } from "@/stores/plugin_run";
import ClusterExploration from "@/components/ClusterExploration.vue";

export default {
  props: ["cluster", "allClusters", "type_name"],
  setup(props) {
    const playerStore = usePlayerStore();
    const pluginRunStore = usePluginRunStore();
    const clusterTimelineItemStore = useClusterTimelineItemStore();

    const loading = ref(false);
    const show = ref(false);
    const renaming = ref(false);
    const isSubmitting = ref(false);
    const showDotMenu = ref(false);
    const mergeDialog = ref(false);
    const toMergeCluster = ref(undefined);
    const renameValue = ref(props.cluster.name);

    const firstOccurence = computed(() => {
      if (props.cluster.items.length > 0) {
        return get_timecode(props.cluster.items[0].time);
      }
      return 0;
    });

    const lastOccurence = computed(() => {
      if (props.cluster.items.length > 0) {
        return get_timecode(props.cluster.items.at(-1).time);
      }
      return 0;
    });

    const mergableClusters = computed(() => {
      return props.allClusters.filter((c) => c.id !== props.cluster.id);
    });

    const thumbnails = computed(() => {
      return props.cluster.items.reduce((arr, item, i) => {
        if (i % Math.ceil(props.cluster.items.length / 4) === 0) {
          arr.push(item);
        }
        return arr;
      }, []);
    });

    const renameCluster = async () => {
      if (renaming.value) return;
      renaming.value = true;

      await clusterTimelineItemStore.rename({
        cluster_id: props.cluster.cluster_id,
        name: renameValue.value,
      });

      renaming.value = false;
      show.value = false;
      showDotMenu.value = false;
    };

    const deleteCluster = async () => {
      if (isSubmitting.value) return;
      isSubmitting.value = true;

      await clusterTimelineItemStore.delete(props.cluster.cluster_id);
      // delete this card
      // Emits event to remove this cluster from parent
      emit("childDeleted", props.cluster.cluster_id);

      isSubmitting.value = false;
      show.value = false;
      showDotMenu.value = false;
    };

    const mergeClusters = () => {
      clusterTimelineItemStore.merge({
        cluster_from_id: props.cluster.cluster_id,
        cluster_to_id: mergableClusters.value[toMergeCluster.value].cluster_id,
      });
      mergeDialog.value = false;
      showDotMenu.value = false;
    };

    const cancelMergeClusters = () => {
      mergeDialog.value = false;
      showDotMenu.value = false;
    };

    const createTimeline = () => {
      loading.value = true;
      let parameters = [
        {
          name: "timeline",
          value: props.cluster.name,
        },
        {
          name: "cluster_timeline_item_id",
          value: props.cluster.id,
        },
      ];

      pluginRunStore.submit({ plugin: "cluster_to_scalar", parameters }).then(() => {
        loading.value = false;
      });

      showDotMenu.value = false;
    };

    const goToFace = (time) => {
      playerStore.setTargetTime(time);
    };

    // OnMounted lifecycle hook
    onMounted(() => {
      if (showDotMenu.value) {
        showDotMenu.value = false;
      }
    });

    return {
      loading,
      show,
      renaming,
      isSubmitting,
      showDotMenu,
      mergeDialog,
      toMergeCluster,
      renameValue,
      firstOccurence,
      lastOccurence,
      mergableClusters,
      thumbnails,
      renameCluster,
      deleteCluster,
      mergeClusters,
      cancelMergeClusters,
      createTimeline,
      goToFace,
    };
  },
  components: {
    ClusterExploration,
  },
};
</script>

<style scoped>
.image-contaniner {
  overflow-x: auto;
  white-space: nowrap;
  justify-content: flex-start;
  gap: 10px;
}
</style>
