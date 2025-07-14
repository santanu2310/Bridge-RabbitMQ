<script setup lang="ts">
import type { FriendBrief } from '@/types/FreindBrief';

const props = defineProps<{
  data: FriendBrief
}>();

function getInitials(name: string) {
  return name
    .split(" ")
    .map((word) => word.charAt(0).toUpperCase())
    .join("");
}
</script>

<template>
  <div
    class="w-full h-full max-h-18 px-2.5 py-1.5 flex items-center cursor-pointer"
  >
    <div class="w-auto h-full aspect-square p-1.5">
      <div class="w-full h-full overflow-hidden rounded-full">
        <img
          v-if="data.profilePicture"
          :src="data.profilePicture"
          alt=""
          class="w-full h-full object-cover"
        />
        <div
          v-else
          class="w-full h-full flex items-center justify-center bg-red-500"
        >
          <span class="w-fit h-fit block text-white text-xs">{{
            getInitials(data.fullName)
          }}</span>
        </div>
      </div>
    </div>
    <div class="h-full flex items-center flex-grow">
      <div class="p-1 flex flex-col flex-grow">
        <span class="text-color-heading text-base/4 font-medium">{{
          data.fullName
        }}</span>
        <span class="text-sm/4 font-normal text-color-text">@{{ data.userName }}</span>
      </div>
      <div class="h-full mx-3 flex items-center">
        <button class="h-2/3 aspect-square rounded bg-color-background-mute text-primary" @click="$emit('addRequestMessage', data.userName)">+</button>
      </div>
    </div>
  </div>
</template>
