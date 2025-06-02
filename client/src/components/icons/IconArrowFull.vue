<script setup lang="ts">
	interface Props {
		size?: number;
		rotate?: number;
	}
	const { size = 60, rotate = 0 } = defineProps<Props>();
</script>

<template>
	<svg
		xmlns="http://www.w3.org/2000/svg"
		viewBox="0 0 24 24"
		fill="currentColor"
		:height="`${size}%`"
		:width="`${size}%`"
		:transform="`rotate(${rotate})`"
	>
		<path
			d="M18.3642 19.7783L19.7784 18.3643L10.1716 8.75734L14 4.92896L4.92889 4.92896L4.9289 14L8.75735 10.1716L18.3642 19.7783Z"
		></path>
	</svg>
</template>
