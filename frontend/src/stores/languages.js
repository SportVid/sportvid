import { defineStore } from "pinia";
import { ref } from "vue";
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

    const currentLanguage = ref(localStorage.getItem("user-language"));

    if (!languages.find((l) => l.code === currentLanguage.value)) {
      locale.value = "en";
      current.value = "en";
      currentLanguage.value = "en";
    }

    const setLanguage = (code) => {
      locale.value = code;
      current.value = code;
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
