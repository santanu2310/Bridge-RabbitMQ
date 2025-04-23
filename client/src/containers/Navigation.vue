<script setup lang="ts">
	import { useUserStore } from "@/stores/user";
	import IconLogo from "@/components/icons/IconLogo.vue";
	import IconMessages from "@/components/icons/IconMessages.vue";
	import IconGroupes from "@/components/icons/IconGroupes.vue";
	import IconFriends from "@/components/icons/IconFriends.vue";

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
			<div
				class="w-auto lg:w-full h-full lg:h-auto p-1 aspect-square lg:mt-2 flex items-center justify-center cursor-pointer"
				@click="$emit('switchContainer', 'chats')"
			>
				<IconMessages :size="35" />
			</div>
			<div
				class="w-auto lg:w-full h-full lg:h-auto p-1 aspect-square flex items-center justify-center cursor-pointer"
			>
				<IconGroupes :size="35" />
			</div>
			<div
				class="w-auto lg:w-full h-full lg:h-auto p-1 aspect-square flex items-center justify-center cursor-pointer"
				@click="$emit('switchContainer', 'friends')"
			>
				<IconFriends :size="35" />
			</div>
		</div>
		<div
			class="w-1/4 lg:w-full h-full lg:h-auto aspect-square flex flex-col items-center"
		>
			<div
				class="lg:w-1/2 h-1/2 lg:h-auto aspect-square mt-3 mb-4 overflow-hidden object-cover rounded-full cursor-pointer"
				@click="$emit('switchContainer', 'profile')"
			>
				<img
					:src="userStore.user.profilePicUrl as string"
					alt=""
					class="w-full h-full"
				/>
			</div>
		</div>
	</div>
</template>
