/**
 * 路由：首页 / 、搜索 /search?word=
 */
import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import SearchView from '../views/SearchView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'home', component: HomeView, meta: { title: '首页' } },
    {
      path: '/search',
      name: 'search',
      component: SearchView,
      meta: { title: '搜索' },
    },
  ],
  scrollBehavior() {
    return { top: 0 }
  },
})

router.afterEach((to) => {
  const t = (to.meta.title as string) || '百科'
  document.title = `${t} · 百科Wiki`
})

export default router
