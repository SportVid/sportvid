<template>
  <v-main>
    <v-container fluid v-if="userStore.role === 'admin'">
      <v-card elevation="2" class="pa-4">
        <v-card-title class="text-h5">{{ $t("admin_panel.title") }}</v-card-title>
        <v-card-text>
          <v-row class="mt-2">
            <v-col cols="12" md="6">
              <v-text-field
                v-model="search"
                :label="$t('admin_panel.search')"
                variant="outlined"
                density="compact"
                clearable
              >
                <template #prepend-inner>
                  <v-icon class="mr-2">mdi-magnify</v-icon>
                </template>
              </v-text-field>
            </v-col>

            <v-col cols="12" md="6">
              <v-select
                v-model="roleFilter"
                :items="roleOptions"
                :label="$t('admin_panel.role.label')"
                variant="outlined"
                density="compact"
                clearable
              >
                <template #prepend-inner>
                  <v-icon class="mr-2">mdi-account-group-outline</v-icon>
                </template>
              </v-select>
            </v-col>
          </v-row>

          <v-data-table
            :headers="headers"
            :items="filteredUsers"
            item-key="id"
            :loading="adminStore.isLoading"
            hide-default-footer
            density="comfortable"
            class="elevation-2"
          >
            <template #item.date_joined="{ value }">
              {{ value.split("T")[0] }}
            </template>
            <template #item.actions="{ item }">
              <v-btn
                size="x-small"
                icon
                color="primary"
                class="mr-1"
                @click="openUpdateModal(item)"
              >
                <v-icon>mdi-pencil</v-icon>
              </v-btn>
              <v-btn
                size="x-small"
                icon
                :color="item.id === userStore.userId ? 'grey' : 'red'"
                :disabled="item.id === userStore.userId"
                @click="openDeleteModal(item)"
              >
                <v-icon>mdi-delete</v-icon>
              </v-btn>
            </template>
          </v-data-table>
        </v-card-text>
      </v-card>
      <ModalAdminUserDelete v-if="editingUser" v-model="showModalDelete" :user="editingUser" />
      <ModalAdminUserUpdate v-if="editingUser" v-model="showModalUpdate" :user="editingUser" />
    </v-container>
  </v-main>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useI18n } from "vue-i18n";
import { useUserStore } from "@/stores/user";
import { useAdminStore } from "@/stores/admin";
import ModalAdminUserDelete from "@/components/admin/ModalAdminUserDelete.vue";
import ModalAdminUserUpdate from "@/components/admin/ModalAdminUserUpdate.vue";

const adminStore = useAdminStore();
const userStore = useUserStore();

const { t } = useI18n();

onMounted(() => {
  adminStore.fetchUsers();
});

const search = ref("");
const roleFilter = ref(null);
const roleOptions = [
  { title: t("admin_panel.role.all"), value: null },
  { title: t("admin_panel.role.admin"), value: "admin" },
  { title: t("admin_panel.role.user"), value: "user" },
];
const filteredUsers = computed(() => {
  let list = adminStore.users;

  if (search.value) {
    const term = search.value.toLowerCase();
    list = list.filter(
      (u) => u.username?.toLowerCase().includes(term) || u.email?.toLowerCase().includes(term)
    );
  }

  if (roleFilter.value) {
    list = list.filter((u) => u.role === roleFilter.value);
  }

  return list;
});

const headers = [
  { title: t("admin_panel.user.id"), value: "id", sortable: true },
  { title: t("admin_panel.user.username"), value: "username", sortable: true },
  { title: t("admin_panel.user.email"), value: "email", sortable: true },
  { title: t("admin_panel.user.role"), value: "role", sortable: true },
  { title: t("admin_panel.user.video_allowance"), value: "video_allowance", sortable: true },
  { title: t("admin_panel.user.file_allowance"), value: "file_allowance", sortable: true },
  { title: t("admin_panel.user.max_video_size"), value: "max_video_size", sortable: true },
  { title: t("admin_panel.user.max_file_size"), value: "max_file_size", sortable: true },
  { title: t("admin_panel.user.date_joined"), value: "date_joined", sortable: true },
  {
    title: t("admin_panel.user.actions"),
    value: "actions",
    sortable: false,
    width: "8%",
    align: "center",
  },
];

const editingUser = ref(null);
const showModalUpdate = ref(false);
const openUpdateModal = (user) => {
  editingUser.value = { ...user };
  showModalUpdate.value = true;
};
const showModalDelete = ref(false);
const openDeleteModal = (user) => {
  editingUser.value = { ...user };
  showModalDelete.value = true;
};
</script>
