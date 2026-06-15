import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/theme-chalk/index.css'
import './style.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import App from './App.vue'

document.documentElement.classList.add('dark')

const app = createApp(App)
app.use(ElementPlus)
app.mount('#app')
