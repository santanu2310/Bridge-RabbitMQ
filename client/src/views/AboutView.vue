<script setup lang="ts">
	import { ref } from "vue";
	import EditProfilePicture from "@/components/EditProfilePicture.vue";
	const profileInputReference = ref<HTMLInputElement | null>(null);
	const editProfilePopup = ref(false);

	const onClose = () => {
		profileInputReference.value = null;
		editProfilePopup.value = false;
	};
</script>

<template>
	<div class="w-full h-full relative">
		<input
			type="file"
			name="profilepic"
			id="profilepic"
			ref="profileInputReference"
			max="20971520"
			accept="image/*"
			@change="editProfilePopup = true"
		/>
	</div>
	<Teleport to="body">
		<EditProfilePicture
			v-if="editProfilePopup"
			:file="profileInputReference?.files![0]"
			@close="onClose"
		/>
	</Teleport>
	{{ editProfilePopup }}
</template>
