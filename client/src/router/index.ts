import { createRouter, createWebHistory } from "vue-router";
import HomeView from "../views/HomeView.vue";
import { useAuthStore } from "@/stores/auth";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/login",
      name: "login",
      component: () => import("../views/LoginView.vue"),
      beforeEnter: () => {
        const authStore = useAuthStore();
        if (authStore.isAuthenticated == true) {
          return { name: "home" };
        }
      },
    },
    {
      path: "/register",
      name: "register",
      component: () => import("../views/RegistrationView.vue"),
      children: [
        {
          path: "",
          name: "register-form",
          component: () => import("../containers/Register.vue"),
        },
        {
          path: "verify",
          name: "verify-email",
          component: () => import("../containers/VerifyEmail.vue"),
        },
      ],
      beforeEnter: () => {
        const authStore = useAuthStore();
        if (authStore.unVerifiedEmail == true) return;
        if (authStore.isAuthenticated == true) {
          return { name: "home" };
        }
      },
    },
    {
      path: "/",
      name: "home",
      component: HomeView,
      beforeEnter: async () => {
        const authStore = useAuthStore();

        if (authStore.isAuthenticated == false) {
          return { name: "login" };
        }
      },
    },
  ],
});

export default router;
