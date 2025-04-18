import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { VTreeview } from 'vuetify/labs/VTreeview';
import '@mdi/font/css/materialdesignicons.css'

export const vuetify = createVuetify({
  components: {
    ...components,
    VTreeview,
  },
  directives,
  theme: {
    defaultTheme: 'light',
    themes: {
      light: {
        colors: {
          primary: '#1D3557',
          secondary: '#457B9D',
          accent: '#E63946',
        }
      },
    },
  },
})
