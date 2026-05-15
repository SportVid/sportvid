import "vuetify/styles";
import { createVuetify } from "vuetify";
import * as components from "vuetify/components";
import { VIcon } from "vuetify/components";
import * as directives from "vuetify/directives";
import { VTreeview } from "vuetify/components";
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
    themes: {
      light: {
        dark: false,
        colors: {
          primary: "#1D3557",
          secondary: "#457B9D",
          accent: "#E63946",
          error: "#ff0000",
          success: "#2E7D32",
          warning: "#E65100",
          info: "#0277BD",
          background: "#FFFFFF",
          surface: "#F5F5F5",
        },
      },
      dark: {
        dark: true,
        colors: {
          primary: "#90CAF9",
          secondary: "#80DEEA",
          accent: "#E63946",
          error: "#ff0000",
          success: "#81C784",
          warning: "#FFB74D",
          info: "#4FC3F7",
          background: "#121212",
          surface: "#3b3b3f",
        },
      },
    },
  },
  locale: {
    adapter: createVueI18nAdapter({ i18n, useI18n }),
  },
  aliases: {
    snackbarIconSuccess: VIcon,
    snackbarIconWarning: VIcon,
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
    snackbarIconSuccess: {
      color: "white",
      size: "large",
      icon: "mdi-check-circle",
      class: "mt-1 mr-2",
    },
    snackbarIconWarning: {
      color: "white",
      size: "large",
      icon: "mdi-alert-circle-outline",
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
