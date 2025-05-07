import "vuetify/styles";
import { createVuetify } from "vuetify";
import * as components from "vuetify/components";
import { VIcon } from "vuetify/components";
import * as directives from "vuetify/directives";
import { VTreeview } from "vuetify/labs/VTreeview";
import "@mdi/font/css/materialdesignicons.css";
import { createVueI18nAdapter } from "vuetify/locale/adapters/vue-i18n";
import { useI18n } from "vue-i18n";
import { i18n } from "./i18n";

export const vuetify = createVuetify({
  components: {
    ...components,
    VTreeview,
  },
  directives,
  theme: {
    defaultTheme: "light",
    options: { customProperties: true },
    themes: {
      light: {
        colors: {
          primary: "#1D3557",
          accent: "#E63946",
        },
      },
    },
  },
  locale: {
    adapter: createVueI18nAdapter({ i18n, useI18n }),
  },
  aliases: {
    snackbarIcon: VIcon,
    tabWindowIcon: VIcon,
    appBarIcon: VIcon,
  },
  defaults: {
    VSnackbar: {
      location: "top",
      timeout: "2000",
      color: "primary",
      multiLine: true,
    },
    snackbarIcon: {
      color: "white",
      size: "large",
      icon: "mdi-check-circle",
      class: "mt-1 mr-2",
    },
    appBarIcon: {
      color: "primary",
    },
    tabWindowIcon: {
      size: "small",
      class: "mb-1",
    },
  },
});
