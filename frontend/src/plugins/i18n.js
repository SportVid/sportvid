import { createI18n } from "vue-i18n";

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

export const i18n = createI18n({
  locale: process.env.VUE_APP_I18N_LOCALE || "en",
  fallbackLocale: process.env.VUE_APP_I18N_FALLBACK_LOCALE || "en",
  messages: loadLocaleMessages(),
  legacy: false,
  warnHtmlMessage: false,
});
