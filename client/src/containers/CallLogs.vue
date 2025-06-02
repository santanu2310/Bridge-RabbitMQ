<script lang="ts" setup>
	import { useCallStore } from "@/stores/call";
	import { useUserStore } from "@/stores/user";
	import CallLog from "@/components/CallLog.vue";

	const callStore = useCallStore();
	const userStore = useUserStore();
</script>
<template>
	<div class="h-full flex flex-col">
		<div class="w-ful p-6 flex items-center">
			<span class="font-medium text-xl">Calls</span>
		</div>
		<div class="flex flex-col overflow-y-auto flex-grow">
			<div
				class="w-full h-auto my-2"
				v-for="record in callStore.callRecords"
			>
				<CallLog :call-record="record" :user-id="userStore.user.id" />
			</div>
		</div>
	</div>
</template>
