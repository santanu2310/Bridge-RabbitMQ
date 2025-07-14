<script setup lang="ts">
import { useUserStore } from "@/stores/user";
import IconSettings from "@/components/icons/IconSettings.vue";
import IconMail from "@/components/icons/IconMail.vue";
import IconLocation from "@/components/icons/IconLocation.vue";
import { getInitials } from "@/utils/StringUtils";
import { getUserColor } from "@/utils/ProfileUtils";

const userStore = useUserStore();
const user = userStore.user;
</script>

<template>
  <div class="w-full h-full p-8">
    <div class="w-full h-8 flex items-center justify-between">
      <span class="font-medium text-xl">Profile</span>
      <button
        class="w-auto h-full aspect-square outline-none border-none flex items-center justify-between"
        @click="$emit('switchContainer', 'settings')"
      >
        <IconSettings />
      </button>
    </div>
    <div class="w-full h-auto aspect-square flex flex-col items-center">
      <div class="w-3/5 h-auto aspect-square rounded-full overflow-hidden">
        <img
          :src="user.profilePicUrl ?? undefined"
          alt=""
          v-if="user.profilePicUrl"
        />
        <div
          v-else
          class="w-full h-full flex items-center justify-center"
          :style="{ background: getUserColor(userStore.user.fullName) }"
        >
          <span class="w-fit h-fit block text-white text-3xl font-semibold">{{
            getInitials(userStore.user.fullName)
          }}</span>
        </div>
      </div>
      <span class="mt-5 text-lg font-semibold">{{ user.fullName }}</span>
      <span class="text-sm text-primary">@{{ user.userName }}</span>
      <span class="mt-5 text-sm font-light">{{ user.bio }}</span>
    </div>
    <div class="mt-5">
      <div class="w-full h-8 flex items-center">
        <div
          class="w-auto h-full aspect-square flex justify-center items-center"
        >
          <IconMail :size="50" />
        </div>
        <span class="block text-sm font-semibold">{{ user.email }}</span>
      </div>
      <div class="w-full h-8 flex items-center">
        <div
          class="w-auto h-full aspect-square flex justify-center items-center"
        >
          <IconLocation :size="50" />
        </div>
        <span class="block text-sm font-semibold">{{ user.location }}</span>
      </div>
    </div>
  </div>
</template>

<style></style>
