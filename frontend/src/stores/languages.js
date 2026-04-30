import { defineStore } from "pinia";
import { ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useLocale } from "vuetify";

export const useLanguageStore = defineStore(
  "language",
  () => {
    const { locale } = useI18n();
    const { current } = useLocale();

    const languages = [
      { code: "en", label: "English", flag: require("@/assets/flags/en.svg") },
      { code: "de", label: "Deutsch", flag: require("@/assets/flags/de.svg") },
    ];

    const currentLanguage = ref("en");

    watch(
      currentLanguage,
      (lang) => {
        locale.value = lang;
        current.value = lang;
      },
      { immediate: true }
    );

    const setLanguage = (code) => {
      currentLanguage.value = code;
    };

    return {
      languages,
      currentLanguage,
      setLanguage,
    };
  },
  {
    persist: {
      pick: ["currentLanguage"],
      storage: localStorage,
    },
  }
);
