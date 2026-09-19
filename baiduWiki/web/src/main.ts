/**
 * 应用入口：先落主题，再挂载 Vue + Router
 */
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { bootstrapTheme } from './theme'
import './styles/base.css'

bootstrapTheme()

createApp(App).use(router).mount('#app')
