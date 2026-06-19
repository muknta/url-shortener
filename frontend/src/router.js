import { createRouter, createWebHistory } from "vue-router";
import ShortenForm from "./components/ShortenForm.vue";
import UrlList from "./components/UrlList.vue";

const routes = [
  { path: "/", component: ShortenForm },
  { path: "/public-urls/", component: UrlList, props: { mode: "public" } },
  { path: "/my-urls/", component: UrlList, props: { mode: "mine" } },
];

export default createRouter({
  history: createWebHistory(),
  routes,
});
