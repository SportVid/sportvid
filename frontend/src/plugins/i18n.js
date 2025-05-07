import { createI18n } from "vue-i18n";
import { en as vuetifyEn, de as vuetifyDe } from "vuetify/locale";

function loadLocaleMessages() {
  const locales = require.context("../locales", true, /[A-Za-z0-9-_,\s]+\.json$/i);
  const messages = {};

  locales.keys().forEach((key) => {
    const matched = key.match(/([A-Za-z0-9-_]+)\./i);

    if (matched && matched.length > 1) {
      messages[matched[1]] = locales(key);
    }
  });

  return messages;
}

const messages = loadLocaleMessages();

if (messages.en) {
  messages.en.$vuetify = {
    ...vuetifyEn,
    dataIterator: {
      rowsPerPageText: "Items per page:",
      pageText: "{0}-{1} of {2}",
    },
  };
}
if (messages.de) {
  messages.de.$vuetify = {
    ...vuetifyDe,
    dataIterator: {
      rowsPerPageText: "Elemente pro Seite:",
      pageText: "{0}-{1} von {2}",
    },
  };
}

export const i18n = createI18n({
  locale: process.env.VUE_APP_I18N_LOCALE,
  fallbackLocale: process.env.VUE_APP_I18N_FALLBACK_LOCALE,
  messages,
  legacy: false,
  warnHtmlMessage: false,
});
