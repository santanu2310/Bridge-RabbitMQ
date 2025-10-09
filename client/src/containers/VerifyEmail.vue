<script setup lang="ts">
import { ref } from "vue";
import { useRouter, RouterLink } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const router = useRouter();
const authStore = useAuthStore();
const otp = ref<string | null>();
const errorMsg = ref<string[]>([]);

async function verify() {
  errorMsg.value = [];
  if (!otp.value || !authStore.email) {
    errorMsg.value.push("OTP is required!");
    return;
  }
  try {
    const response = await authStore.publicAxios({
      method: "post",
      url: "users/verify-email",
      data: {
        email: authStore.email,
        otp: otp.value,
      },
    });

    if (response.status === 200) {
      router.push({ name: "login" });
    }
  } catch (error) {
    console.error(error);
    const axiosError = error as {
      response: { data: { detail: string } };
    };
    errorMsg.value.push(axiosError.response.data.detail);
  }
}
</script>

<template>
  <div class="login-form max-w-80 w-full mb-20 flex flex-col items-center">
    <div class="mt-12 mb-4 text-center">
      <b class="text-3xl font-medium">Verify Email</b>
      <p class="mt-1 text-base">Enter the OTP sent to your email.</p>
      <div class="w-full h-fit flex mt-4 justify-center">
        <span
          v-for="msg in errorMsg"
          class="text-red-500 text-sm font-medium"
          >{{ msg }}</span
        >
      </div>
    </div>
    <form class="w-full" method="post" @submit.prevent="verify()">
      <div class="input-div">
        <label class="text-base font-medium" for="otp">OTP</label>
        <input
          type="text"
          id="otp"
          v-model="otp"
          placeholder="Enter OTP"
          required
        />
      </div>
      <button type="submit" class="button w-full h-10 rounded-lg font-medium">
        Verify
      </button>
    </form>
  </div>
  <div class="text-center">
    <span class="text-sm md:text-base">
      © 2024 Bridge. Crafted with <b class="text-white">❤️</b> by Santanu
    </span>
  </div>
</template>

<style scoped>
.login {
  background: var(--primary);
}

.login-f-wrapper {
  background-color: var(--color-background-mute);
}

.login-form > div > b {
  color: var(--color-heading);
}

.input-div {
  width: 100%;
  height: auto;
  margin-bottom: 20px;
  display: flex;
  flex-direction: column;
}

.input-div > label {
  color: var(--color-heading);
}

input {
  width: 100%;
  margin-top: 10px;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  font-size: 0.875rem;
  line-height: 1.5rem;
  font-weight: 400;
  border: none;
  outline: none;
  background: var(--color-background);
  color: var(--color-text);
}

.button {
  background: var(--primary);
  color: var(--color-background);
}

.link {
  color: var(--primary);
}

.logo {
  color: var(--color-text);
}

.auth-img {
  max-width: 160%;
}

@media (max-width: 1280px) {
  .auth-img {
    max-width: 140%;
  }
}
</style>
