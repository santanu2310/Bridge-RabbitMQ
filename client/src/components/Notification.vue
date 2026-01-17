<script setup lang="ts">
import { useAuthStore } from "@/stores/auth";
import { useFriendStore } from "@/stores/friend";
import Avatar from "@/components/ui/Avatar.vue";
import IconClose from "@/components/icons/IconClose.vue";
import IconTick from "@/components/icons/IconTick.vue";
import { mapResponseToUser } from "@/types/User";

const authStore = useAuthStore();
const friendStore = useFriendStore();

async function acceptRequest(request_id: string) {
  try {
    const response = await authStore.authAxios({
      method: "patch",
      url: `friends/accept-request/${request_id}`,
    });
    console.log(response.status);

    if (response.status === 200) {
      console.log(response.data);

      friendStore.friendRequests = friendStore.friendRequests.filter(
        (request) => request.id === request_id
      );

      friendStore.addFriend(response.data.friendship_document_id);
    }
  } catch (error) {
    console.error(error);
  }
}
async function rejectRequest(request_id: string) {
  try {
    const response = await authStore.authAxios({
      method: "patch",
      url: `friends/reject-request/${request_id}`,
    });

    if (response.status === 200) {
      friendStore.friendRequests = friendStore.friendRequests.filter(
        (request) => request.id != request_id
      );
    }
  } catch (error) {
    console.error(error);
  }
}
const props = defineProps<{
  id: string;
  name: string;
  message: string;
}>();
</script>
<template>
  <div class="w-full h-20 flex items-center px-3 py-2">
    <div class="h-[70%] w-auto aspect-square overflow-hidden rounded-full">
      <Avatar :profileUrl="null" :userName="name" />
    </div>
    <div class="h-auto flex flex-col flex-grow items-start text-sm px-2">
      <span class="font-medium">{{ name }}</span>
      <span class="font-light">{{ message }}</span>
    </div>
    <div class="w-1/4 min-h-9 h-2/3 mt-2 flex justify-between">
      <button
        class="btn border-red-500 text-red-500"
        @click="rejectRequest(id)"
      >
        <IconClose />
      </button>
      <button class="btn bg-primary border-primary" @click="acceptRequest(id)">
        <IconTick />
      </button>
    </div>
  </div>
</template>

<style scoped>
.btn {
  width: auto;
  height: 75%;
  aspect-ratio: 1;
  border-radius: 50%;
  border-width: 1px;
  border-style: solid;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
