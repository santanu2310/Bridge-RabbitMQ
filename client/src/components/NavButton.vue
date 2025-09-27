<script setup lang="ts">
const props = defineProps<{
  text: string;
  badge?: boolean | null;
}>();
</script>

<template>
  <div
    class="w-auto h-full lg:w-full lg:h-auto group relative inline-flex items-center justify-center cursor-pointer"
  >
    <span
      v-if="badge"
      class="w-2 h-auto aspect-square overflow-hidden rounded-full bg-red-500 absolute top-[22%] right-[22%] block"
    ></span>
    <div
      class="w-auto lg:w-full h-full lg:h-auto p-1 aspect-square flex items-center justify-center"
    >
      <slot></slot>
    </div>

    <!-- Tooltip -->
    <div
      class="absolute left-full -ml-1 hidden group-hover:block whitespace-nowrap bg-gray-950 text-gray-100 text-sm px-3 py-1.5 rounded shadow-lg z-50 before:absolute before:right-full before:top-1/2 before:-translate-y-1/2 before:border-8 before:border-r-gray-950 before:border-l-transparent before:border-t-transparent before:border-b-transparent"
    >
      {{ props.text }}
    </div>
  </div>
</template>
