<script setup lang="ts">
	import { ref } from "vue";

	import IconLogo from "@/components/icons/IconLogo.vue";
	import IconMessages from "@/components/icons/IconMessages.vue";
	import IconGroupes from "@/components/icons/IconGroupes.vue";
	import IconFriends from "@/components/icons/IconFriends.vue";

	import Chats from "@/containers/Chats.vue";
	import Friends from "@/containers/Friends.vue";
	import Profile from "@/containers/Profile.vue";
	import FriendRequests from "@/containers/FriendRequests.vue";
	import Settings from "@/containers/Settings.vue";
	import Conversation from "@/containers/Conversation.vue";

	import { useUserStore } from "@/stores/user";

	const userStore = useUserStore();

	const leftContent = ref<string>("chats");

	function switchContainer(n: string) {
		leftContent.value = n;
	}
</script>

<template>
	<main class="w-full min-h-full flex">
		<div
			class="navigation md:w-12 lg:w-16 h-full flex flex-col justify-between"
		>
			<div class="w-full h-fit flex flex-col items-end">
				<div
					class="logo w-full h-auto aspect-square flex items-center justify-center"
				>
					<IconLogo />
				</div>
				<div
					class="w-full h-auto aspect-icon mt-2 flex items-center justify-center cursor-pointer"
					@click="leftContent = 'chats'"
				>
					<IconMessages :size="35" />
				</div>
				<div
					class="w-full h-auto aspect-icon mt-2 flex items-center justify-center cursor-pointer"
				>
					<IconGroupes :size="35" />
				</div>
				<div
					class="w-full h-auto aspect-icon mt-2 flex items-center justify-center cursor-pointer"
					@click="leftContent = 'friends'"
				>
					<IconFriends :size="35" />
				</div>
			</div>
			<div class="w-full h-auto aspect-square flex flex-col items-center">
				<!-- <div
					class="w-full h-auto aspect-icon mt-2 flex items-center justify-center cursor-pointer"
					@click="leftContent = 'notification'"
				>
					<IconBell :size="35" />
				</div> -->
				<div
					class="w-1/2 h-auto aspect-square mt-3 mb-4 overflow-hidden object-cover rounded-full cursor-pointer"
					@click="leftContent = 'profile'"
				>
					<img
						:src="userStore.user.profilePicUrl as string"
						alt=""
						class="w-full h-full"
					/>
				</div>
			</div>
		</div>
		<div class="left-sidebar md:w-72 lg:w-96 h-full">
			<Chats v-if="leftContent == 'chats'" />
			<Friends
				v-if="leftContent == 'friends'"
				@freind-request="leftContent = 'notification'"
			/>
			<Profile
				v-if="leftContent == 'profile'"
				@switch-container="switchContainer"
			/>
			<FriendRequests
				v-if="leftContent == 'notification'"
				@friends="leftContent = 'friends'"
			/>
			<Settings v-if="leftContent == 'settings'" />
		</div>
		<div class="message">
			<Conversation v-if="userStore.currentConversation" />
		</div>
	</main>
</template>

<style scoped>
	.logo {
		color: var(--primary);
	}

	.navigation {
		background: var(--color-background-soft);
	}

	.aspect-icon {
		aspect-ratio: 7/6;
	}

	.message {
		width: calc(100% - 20rem);
		background-color: var(--color-background-soft);
		background-image: url(../assets/background.png);
	}
</style>
