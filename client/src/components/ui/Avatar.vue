<script setup lang="ts">
import { getInitials } from "@/utils/StringUtils";
import { getUserColor } from "@/utils/ProfileUtils";

const props = defineProps<{
  userName: string;
  profilePicUrl?: string;
}>();

const initials = getInitials(props.userName);
console.log(props.userName);
console.log(initials);
</script>

<template>
  <div class="w-full h-auto aspect-square overflow-hidden rounded-full">
    <img
      v-if="profilePicUrl"
      :src="profilePicUrl"
      :alt="initials"
      class="w-full h-full object-cover"
    />
    <div
      v-else
      class="w-full h-full flex items-center justify-center"
      :style="{ background: getUserColor(userName) }"
    >
      <span class="w-fit h-fit block text-white text-xs">{{ initials }}</span>
    </div>
  </div>
</template>
