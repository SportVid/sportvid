<template>
  <div>
    <v-dialog v-model="show" width="90%" persistent>
      <template v-slot:activator="{ props }">
        <v-btn v-bind="props" text block large>
          <v-icon left>{{ "mdi-eye-outline" }}</v-icon>
          {{ $t("button.edit") }}
        </v-btn>
      </template>
      <v-card v-show="show" class="canvasContainer" ref="canvasContainer">
        <v-card-title>Cluster {{ cluster.name }} </v-card-title>
        <v-card-subtitle>Click on images to mark them for deletion. There are {{ cluster.items.length }} images in total.</v-card-subtitle>
        <v-virtual-scroll
          :items="items"
          height="600px"
          item-height="170px"
        >
          <template v-slot:default="{ item }">
            <v-list-item :key="item.name">
              <v-list-item-content>
                <v-list-item-title>
                  {{ item.name }}
                </v-list-item-title>
                <div style="display: flex; overflow-y: auto; padding: 5px 0;">
                  <img class="clusterImg" v-for="imageUrl in item.visibleImages" :key="imageUrl" :src="imageUrl"
                    :style="borderStyle(imageUrl)" @click="mark(imageUrl)" loading="lazy"/>
                </div>
              </v-list-item-content>
              <v-list-item-action>
                <v-btn
                  v-if="!item.show"
                  icon
                  @click="showItems(item)"
                >
                  <v-icon x-large>mdi-chevron-right</v-icon>
                </v-btn>
              </v-list-item-action>
            </v-list-item>
            <v-divider></v-divider>
          </template>
        </v-virtual-scroll>
        <v-card-actions variant="tonal">
          <v-btn @click="abort"> {{ $t("button.cancel") }} </v-btn>
          <v-spacer></v-spacer>
          <v-btn :disabled="!imagesSelectedForDeletion" @click="showConfirmation = true">
            {{ $t("button.delete") }}
          </v-btn>
          <v-btn :disabled="!imagesSelectedForDeletion" @click="showNewCluster = true">
            {{ $t('modal.cluster_edit.new_cluster') }}
          </v-btn>
          <v-btn :disabled="!imagesSelectedForDeletion" @click="showMove = true">
            {{ $t('modal.cluster_edit.move') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    <v-dialog v-model="showConfirmation" width="auto">
      <v-card>
        <v-card-title>
          Confirm
        </v-card-title>
        <v-card-text>
          Delete {{ markedForDeletion.length }} images from Cluster "{{ cluster.name }}"?
          <v-card-text style="color: red" v-if="allImagesMarked"> <b>You selected all images. This removes the
              cluster.</b></v-card-text>
        </v-card-text>
        <v-card-actions>
          <v-btn @click="showConfirmation = false"> Back </v-btn>
          <v-spacer></v-spacer>
          <v-btn @click="applyDeletion"> Confirm </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    <v-dialog v-model="showMove" width="300px">
      <v-card>
        <v-card-title>
          {{ $t('modal.cluster_edit.move_existing') }}
        </v-card-title>
        <v-card-text>
          <v-list dense>
            <v-subheader>Clusters</v-subheader>
            <v-list-item-group
              v-model="toMoveCluster"
              color="primary"
              style="max-height: 500px; overflow-x: auto;"
            >
              <v-list-item
                v-for="cluster in allClustersButSelf"
                :key="cluster.id"
              >
                <v-list-item-content>
                  <v-list-item-title>{{ cluster.name }}</v-list-item-title>
                </v-list-item-content>
              </v-list-item>
            </v-list-item-group>
          </v-list>
        </v-card-text>
        <v-card-actions>
          <v-btn @click="showMove = false">{{  $t('button.cancel') }}</v-btn>
          <v-spacer></v-spacer>
          <v-btn :disabled="toMoveCluster === undefined" @click="applyMove">{{ $t('modal.cluster_edit.move') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    <v-dialog v-model="showNewCluster" width="300px">
      <v-card>
        <v-card-title>
          {{ $t('modal.cluster_edit.move_new') }}
        </v-card-title>
        <v-card-text>
          <v-text-field
            label="Cluster Name"
            v-model="newClusterName"
          ></v-text-field>
        </v-card-text>
        <v-card-actions>
          <v-btn @click="showNewCluster = false">{{ $t('button.cancel') }}</v-btn>
          <v-spacer></v-spacer>
          <v-btn :disabled="newClusterName.length == 0" @click="applyNewCluster">{{ $t('button.create') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from "vue";
import { useClusterTimelineItemStore } from '../stores/cluster_timeline_item';
import { useShotStore } from '../stores/shot';

export default {
  props: ["cluster", "allClusters"],
  setup(props) {
    const show = ref(false);
    const showConfirmation = ref(false);
    const showNewCluster = ref(false);
    const newClusterName = ref('');
    const showMove = ref(false);
    const toMoveCluster = ref(undefined);
    const markedForDeletion = ref([]);
    const items = ref([]);

    const clusterTimelineItemStore = useClusterTimelineItemStore();
    const shotStore = useShotStore();

    const allImagesMarked = computed(() => markedForDeletion.value.length === items.value.length);
    const imagesSelectedForDeletion = computed(() => markedForDeletion.value.length > 0);
    const allClustersButSelf = computed(() => props.allClusters.filter(c => c.id !== props.cluster.id));

    const generateItems = () => {
      items.value = shotStore.shots.map((shot, i) => {
        const images = props.cluster.items.filter((i) => Math.round(shot.start) <= Math.round(i.time) && Math.round(i.time) < Math.round(shot.end)).map((i) => i.image_path);
        return {
          name: "Shot " + i,
          images: images,
          start: shot.start,
          end: shot.end,
          visibleImages: images.slice(0, 5),
          show: images.length <= 5
        };
      }).filter((s) => s.images.length > 0);
    };

    const showItems = (item) => {
      item.show = true;
      item.visibleImages = item.images;
    };

    const marked = (imageUrl) => {
      return markedForDeletion.value.includes(imageUrl);
    };

    const mark = (imageUrl) => {
      if (marked(imageUrl)) {
        markedForDeletion.value = markedForDeletion.value.filter((e) => e != imageUrl);
      } else {
        markedForDeletion.value.push(imageUrl);
      }
    };

    const borderStyle = (imageUrl) => {
      if (marked(imageUrl)) {
        return 'border: 5px solid red';
      }
      return '';
    };

    const applyMove = async () => {
      const marked_items = props.cluster.items.filter((i) => markedForDeletion.value.includes(i.image_path))
                                               .map((i) => i.id);
      await clusterTimelineItemStore.moveItemsToCluster(
        props.cluster.cluster_id,
        marked_items,
        allClustersButSelf.value[toMoveCluster.value].cluster_id
      );
      show.value = false;
      markedForDeletion.value = [];
      showMove.value = false;
      if (allImagesMarked.value) {
        this.$emit("deleteCluster");
      }
    };

    const applyNewCluster = async () => {
      const marked_items = props.cluster.items.filter((i) => markedForDeletion.value.includes(i.image_path))
                                               .map((i) => i.id);
      const newCluster = await clusterTimelineItemStore.create(
        newClusterName.value,
        props.cluster.video,
        props.cluster.plugin_run,
        props.cluster.type
      )
      if (newCluster) {
        await clusterTimelineItemStore.moveItemsToCluster(
          props.cluster.cluster_id,
          marked_items,
          newCluster.cluster_id
        );
      }
      show.value = false;
      markedForDeletion.value = [];
      newClusterName.value = '';
      showNewCluster.value = false;
      if (allImagesMarked.value) {
        this.$emit("deleteCluster");
      }
    };

    const applyDeletion = async () => {
      const item_ids_to_delete = props.cluster.items.filter((i) => markedForDeletion.value.includes(i.image_path))
                                                   .map((i) => i.id);
      await clusterTimelineItemStore.deleteItems(props.cluster.cluster_id, item_ids_to_delete);

      markedForDeletion.value = [];
      showConfirmation.value = false;
      show.value = false;
      if (allImagesMarked.value) {
        this.$emit("deleteCluster");
      }
    };

    const abort = () => {
      markedForDeletion.value = [];
      show.value = false;
    };

    onMounted(() => {
      generateItems();
    });

    watch(() => shotStore.shots, () => {
      generateItems();
    });

    watch(() => props.cluster.items, () => {
      generateItems();
    });

    return {
      show,
      showConfirmation,
      showNewCluster,
      newClusterName,
      showMove,
      toMoveCluster,
      markedForDeletion,
      items,
      allImagesMarked,
      imagesSelectedForDeletion,
      allClustersButSelf,
      generateItems,
      showItems,
      mark,
      borderStyle,
      applyMove,
      applyNewCluster,
      applyDeletion,
      abort
    };
  }
};
</script>

<style>
.scrollable-content {
  max-height: 70vh;
  margin-bottom: 5px;
}

.clusterImg {
  margin: 5px;
  height: 100px;
}

.canvasContainer {
  background: white;
}
</style>