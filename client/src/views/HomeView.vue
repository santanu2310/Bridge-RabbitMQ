<script setup lang="ts">
	import { ref, onMounted, onUnmounted } from "vue";

	import Chats from "@/containers/Chats.vue";
	import Friends from "@/containers/Friends.vue";
	import Profile from "@/containers/Profile.vue";
	import FriendRequests from "@/containers/FriendRequests.vue";
	import Settings from "@/containers/Settings.vue";
	import Conversation from "@/containers/Conversation.vue";
	import Navigation from "@/containers/Navigation.vue";
	import AudioCall from "@/containers/AudioCall.vue";

	import { useUserStore } from "@/stores/user";

	const userStore = useUserStore();
	const width = ref<number>(window.innerWidth);
	console.log(width.value);

	const leftContent = ref<string>("chats");
	const rightContent = ref<string | null>(null);

	const onResize = () => {
		width.value = window.innerWidth;

		if (width.value > 1024) {
			userStore.isChatVisible = true;
		}
	};

	function switchContainer(n: string) {
		leftContent.value = n;
	}

	onMounted(() => {
		window.addEventListener("resize", onResize);
	});
	onUnmounted(() => {
		window.removeEventListener("resize", onResize);
	});
</script>

<template>
	<main class="w-full min-h-full flex relative">
		<div
			class="w-full lg:w-[21rem] xl:w-[23.5rem] flex flex-col-reverse lg:flex-row"
			v-if="userStore.isChatVisible == false || width > 1024"
		>
			<div class="lg:w-12 xl:w-14 h-16 lg:h-full lg:block">
				<Navigation @switch-container="switchContainer" />
			</div>
			<div class="lg:w-72 xl:w-80 h-full">
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
		</div>
		<div
			v-if="userStore.isChatVisible || width > 1024"
			class="message w-full flex flex-grow bg-color-background-soft"
		>
			<Conversation v-if="userStore.currentConversation" />
		</div>
		<div
			class="lg:w-[40rem] xl:w-[44rem]"
			v-if="userStore.ongoingCall?.minimised == false"
		>
			<AudioCall v-if="userStore.ongoingCall?.minimised == false" />
		</div>
	</main>
</template>

<style scoped>
	.showChat {
		height: 100%;
		display: flex !important;
	}

	.hideChat {
		display: none;
	}
	.message {
		background-image: url(../assets/background.png);
	}
</style>
