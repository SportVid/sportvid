import { defineStore } from "pinia";
import { ref, computed } from "vue";

export const useErrorStore = defineStore("error", () => {
  const error_component = ref(null);
  const error_code = ref(null);
  const error_date = ref(null);
  const error = ref(false);

  const errorMessage = computed(() => {
    return `(${error_date.value}) ${error_component.value}: ${error_code.value}`;
  });

  const setError = (component, code) => {
    error_component.value = component;
    error_code.value = code;
    error_date.value = new Date();
    error.value = true;
  };

  return {
    error_component,
    error_code,
    error_date,
    error,
    errorMessage,
    setError,
  };
});
