<script setup lang="ts">
import { useUserStore } from "@/stores/user";
import IconLogo from "@/components/icons/IconLogo.vue";
import IconMessages from "@/components/icons/IconMessages.vue";
import IconGroupes from "@/components/icons/IconGroupes.vue";
import IconFriends from "@/components/icons/IconFriends.vue";
import IconCall from "@/components/icons/IconCall.vue";
import NavButton from "@/components/NavButton.vue";

const userStore = useUserStore();
</script>

<template>
  <div
    class="w-full h-full flex flex-row lg:flex-col justify-between bg-color-background-soft"
  >
    <div
      class="w-3/4 lg:w-full lg:h-fit flex justify-around lg:flex-col items-end"
    >
      <div
        class="w-full h-auto aspect-square hidden lg:flex items-center justify-center text-primary"
      >
        <IconLogo />
      </div>

      <NavButton
        :text="'Conversations'"
        @click="$emit('switchContainer', 'chats')"
      >
        <IconMessages :size="35" />
      </NavButton>

      <NavButton :text="'Groups'"><IconGroupes :size="35" /></NavButton>
      <NavButton :text="'Friends'" @click="$emit('switchContainer', 'friends')">
        <IconFriends :size="35" />
      </NavButton>
      <NavButton :text="'Calls'" @click="$emit('switchContainer', 'calllogs')">
        <IconCall :size="35" />
      </NavButton>
    </div>
    <div
      class="w-1/4 lg:w-full h-full lg:h-auto aspect-square flex flex-col items-center"
    >
    <NavButton :text="'Profile'" @click="$emit('switchContainer', 'profile')">
      <div class="w-auto lg:w-3/5 h-3/5 lg:h-auto aspect-square overflow-hidden rounded-full cursor-pointer">
        <img
          :src="userStore.user.profilePicUrl as string"
          alt=""
          class="w-full h-full object-cover"
        />
      </div>
      
    </NavButton>
    </div>
  </div>
</template>
