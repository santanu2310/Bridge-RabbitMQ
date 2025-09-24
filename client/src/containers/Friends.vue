<script setup lang="ts">
import { computed, ref } from "vue";
import type { Ref } from "vue";
import { useFriendStore } from "@/stores/friend";
import { useAuthStore } from "@/stores/auth";
import type { User } from "@/types/User";
import { type FriendBrief, mapResponseToUserBrief } from "@/types/FreindBrief";
import Friend from "@/components/Friend.vue";
import FriendPreview from "@/components/FriendPreview.vue";
import IconBell from "@/components/icons/IconBell.vue";
import IconSearch from "@/components/icons/IconSearch.vue";
import IconClose from "@/components/icons/IconClose.vue";
import IconSend from "@/components/icons/IconSend.vue";
import IconBuffer from "@/components/icons/IconBuffer.vue";
import IconTick from "@/components/icons/IconTick.vue";

const friendStore = useFriendStore();
const authStore = useAuthStore();

const addFriendMode = ref(false);
const showFriendRequestModal = ref(false);

const friendBriefs = ref<FriendBrief[] | null>(null);

const username: Ref<string | null> = ref(null);
const message: Ref<string | null> = ref(null);
const requestStatus = ref<"pending" | "sending" | "send" | "failed">("pending");

const emit = defineEmits(["freindRequest"]);

const groupedFriends = computed(() => {
  //Sort the friends object to a sorted array
  const sorted: User[] = Object.values(friendStore.friends).sort((a, b) => {
    const aName = a.fullName || "";
    const bName = b.fullName || "";
    return aName.localeCompare(bName);
  });

  const groups: { initial: string; users: typeof sorted }[] = [];
  let lastInitial = "";

  sorted.forEach((user) => {
    const initial = user.fullName?.[0] || "";
    if (initial !== lastInitial) {
      groups.push({ initial, users: [user] });
      lastInitial = initial;
    } else {
      groups[groups.length - 1].users.push(user);
    }
  });

  return groups;
});

async function createFriendRequest() {
  if (requestStatus.value == "sending") return;
  try {
    requestStatus.value = "sending";
    const response = await authStore.authAxios({
      method: "post",
      url: "friends/make-request",
      data: {
        username: username.value,
        message: message.value,
      },
    });

    if (response.status === 201) {
      requestStatus.value = "send";
      console.log("status 201");
      await new Promise((resolve) => setTimeout(resolve, 500));
      showFriendRequestModal.value = false;
    }
  } catch (error) {
    requestStatus.value = "failed";
    console.error(error);
  }
}

function addRequestMessage(userName: string) {
  showFriendRequestModal.value = true;
  username.value = userName;
}

async function searchUsers(query: string | null) {
  if (query == null) return;
  const response = await authStore.authAxios({
    method: "get",
    url: `friends/search?q=${query}`,
  });
  if (response.status === 200) {
    friendBriefs.value = response.data.map((user: any) =>
      mapResponseToUserBrief(user)
    );
  }
}
</script>

<template>
  <div class="">
    <!-- Header with conditional Add Friend / Friends -->
    <div class="w-full p-6 flex items-center justify-between">
      <span class="font-medium text-xl" v-if="addFriendMode">Add Friend</span>
      <span class="font-medium text-xl" v-else>Friends</span>

      <div class="h-8 flex">
        <button
          class="h-full aspect-square mr-3 flex items-center justify-center"
          @click="$emit('freindRequest')"
        >
          <IconBell :size="55" />
        </button>

        <button
          class="h-full aspect-square rounded bg-color-background-mute text-primary flex items-center justify-center"
          @click="addFriendMode = false"
          v-if="addFriendMode"
        >
          <IconClose :size="50" />
        </button>

        <button
          class="h-full aspect-square rounded bg-color-background-mute text-primary flex items-center justify-center"
          @click="addFriendMode = true"
          v-else
        >
          +
        </button>
      </div>
    </div>

    <!-- Add Friend Prompt -->
    <div class="w-full h-full" v-if="addFriendMode">
      <div class="w-full h-auto flex px-4">
        <input
          class="w-[87%] h-10 px-3 rounded-l-md bg-color-background-mute border-none outline-none"
          type="text"
          placeholder="username"
          v-model="username"
          required
        />
        <button
          class="h-10 w-[13%] bg-primary rounded-r-md flex justify-center items-center"
          @click="searchUsers(username)"
        >
          <IconSearch :size="50" />
        </button>
      </div>

      <div class="w-full h-auto mt-4">
        <div class="w-full h-16" v-for="user in friendBriefs">
          <FriendPreview
            :data="user"
            @add-request-message="addRequestMessage"
          />
        </div>
      </div>
    </div>

    <!-- Friend List -->
    <div class="w-full h-auto" v-else>
      <div
        class="w-full my-3 pl-6"
        v-for="group in groupedFriends"
        :key="group.initial"
      >
        <div class="w-full h-8 mt-2 flex items-center">
          <span class="w-fit mr-2 flex text-primary text-xs font-medium">
            {{ group.initial }}
          </span>
          <span
            class="w-auto bg-color-background-mute flex flex-grow"
            style="height: 1px"
          ></span>
        </div>
        <div v-for="user in group.users" :key="user.id" class="w-full pr-6">
          <Friend
            :id="user.id"
            :display-name="user.fullName"
            :img-url="user.profilePicUrl"
          />
        </div>
      </div>
    </div>

    <div
      class="modal-bg w-screen h-screen fixed top-0 left-0 flex items-center justify-center bg-slate-950 bg-opacity-80"
      v-if="showFriendRequestModal"
      @click="showFriendRequestModal = false"
    >
      <div
        class="w-[650px] max-w-full h-auto p-8 flex flex-col items-center bg-color-background rounded-sm"
        @click.stop
      >
        <h4 class="font-semibold text-base">
          REQUESTING TO <span class="text-primary">@{{ username }}</span>
        </h4>
        <div class="w-full h-auto my-3 flex items-center justify-evenly">
          <input
            class="w-[85%] h-10 rounded-md px-2 bg-color-background-mute outline-none border-none"
            type="text"
            placeholder="message"
            v-model="message"
          />

          <button
            class="w-[10%] h-10 rounded-md p-2 bg-primary flex items-center justify-center"
            @click="createFriendRequest()"
          >
            <IconSend
              v-if="requestStatus == 'failed' || requestStatus == 'pending'"
            />
            <IconBuffer v-else-if="requestStatus == 'sending'" />
            <IconTick :size="90" v-else />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
