import { createApp } from 'vue';
import App from './App.vue';
import './style.css';
import { createI18n } from 'vue-i18n';
import fr from '../translations/fr.json';
import en from '../translations/en.json';

const i18n = createI18n({
  locale: 'fr',
  fallbackLocale: 'en',
  messages: { fr, en }
});

const app = createApp(App);
app.use(i18n);
app.mount('#app'); 