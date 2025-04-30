<script setup lang="ts">
	import IconCall from "@/components/icons/IconCall.vue";
	import IconMic from "@/components/icons/IconMic.vue";
	import IconMicOff from "@/components/icons/IconMicOff.vue";
	import IconSpeaker from "@/components/icons/IconSpeaker.vue";
	import IconArrow from "@/components/icons/IconArrow.vue";

	import type { User } from "@/types/User";

	import { useUserStore } from "@/stores/user";
	import { useFriendStore } from "@/stores/friend";
	import { ref, onMounted } from "vue";

	const userStore = useUserStore();
	const friendStore = useFriendStore();

	const userData = ref<User | null>(null);

	onMounted(() => {
		userData.value =
			friendStore.friends[userStore.ongoingCall!.participants[0]];

		console.log(userData);
	});
</script>
<template>
	<div class="w-full max-w-[1024px] h-full flex flex-col">
		<div class="w-full h-8 px-3 pt-2 flex items-center justify-between">
			<button
				class="h-full aspect-square rounded-md flex items-center justify-center -rotate-90 lg:rotate-180"
			>
				<IconArrow />
			</button>
		</div>
		<div
			class="h-auto m-2 rounded-xl flex items-center justify-center flex-grow bg-color-background-soft"
		>
			<div
				class="w-4/5 h-auto m-3 flex flex-col items-center justify-center"
			>
				<span class="text-xl font-semibold"
					>{{ userData?.fullName }}
				</span>
				<span class="my-3 text-xs font-medium">11:26</span>
				<div
					class="w-3/4 h-auto aspect-square rounded-full overflow-hidden"
				>
					<img :src="userData?.profilePicUrl ?? undefined" alt="" />
				</div>
			</div>
		</div>
		<div class="w-full h-16 flex items-center justify-around">
			<button
				class="h-3/4 w-auto aspect-square rounded-full flex items-center justify-center cursor-pointer duration-200 hover:bg-color-background-mute"
			>
				<IconSpeaker :size="40" />
			</button>
			<button
				class="h-3/4 w-auto aspect-square rounded-full flex items-center justify-center cursor-pointer duration-200 hover:bg-color-background-mute"
			>
				<IconMic :size="40" />
			</button>
			<button
				class="h-3/4 w-auto aspect-square rounded-full flex items-center justify-center cursor-pointer duration-200 bg-red-500 text-color-white"
			>
				<IconCall :size="40" :rotate="135" />
			</button>
		</div>
	</div>
</template>
