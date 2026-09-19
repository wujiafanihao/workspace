/**
 * 应用入口：挂载 Vue + Router，引入基础样式
 */
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './styles/base.css'

createApp(App).use(router).mount('#app')
