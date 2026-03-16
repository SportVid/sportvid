<template>
  <v-dialog v-model="dialog" width="600px">
    <v-card>
      <v-toolbar color="primary">
        <v-toolbar-title class="text-h6">
          {{ $t("modal.admin.delete_account.title") }}
        </v-toolbar-title>

        <template #append>
          <v-btn icon="mdi-close" @click="dialog = false" variant="plain" color="grey" />
        </template>
      </v-toolbar>

      <v-card-text class="text-center">
        <div
          v-html="$t('modal.admin.delete_account.confirmation', { username: props.user.username })"
        />

        <v-btn
          color="error"
          class="mt-2"
          block
          variant="tonal"
          @click="confirmDelete(props.user.id)"
          >{{ $t("button.delete") }}
        </v-btn>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, watch } from "vue";
import { useAdminStore } from "@/stores/admin";

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  user: {
    type: Object,
    required: true,
  },
});
const emit = defineEmits();
const adminStore = useAdminStore();

const dialog = ref(props.modelValue);

watch(
  () => dialog.value,
  (value) => {
    emit("update:modelValue", value);
  }
);
watch(
  () => props.modelValue,
  (value) => {
    if (value) {
      dialog.value = true;
    }
  }
);

const confirmDelete = async (userId) => {
  if (adminStore.isLoading) return;
  try {
    const res = await adminStore.deleteUser({ id: userId, update_type: "admin" });
    if (res && res.status === "ok") {
      adminStore.users = adminStore.users.filter((u) => u.id !== userId);
      dialog.value = false;
    } else {
      console.error("Delete failed", res);
    }
  } catch (err) {
    console.error("Delete error", err);
  }
};
</script>
