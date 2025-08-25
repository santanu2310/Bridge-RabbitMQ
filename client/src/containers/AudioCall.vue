<script setup lang="ts">
import IconCall from "@/components/icons/IconCall.vue";
import IconMic from "@/components/icons/IconMic.vue";
import IconMicOff from "@/components/icons/IconMicOff.vue";
import IconSpeaker from "@/components/icons/IconSpeaker.vue";
import IconArrow from "@/components/icons/IconArrow.vue";

import type { User } from "@/types/User";

import { useCallStore } from "@/stores/call";
import { useFriendStore } from "@/stores/friend";
import { useUserStore } from "@/stores/user";
import { ref, watch, onMounted, onBeforeUnmount } from "vue";

const callStore = useCallStore();
const friendStore = useFriendStore();
const userStore = useUserStore();

const userData = ref<User | null>(null);

const audioElement = ref<HTMLAudioElement>();
const unMute = ref<boolean>(true);
let cleanupWatcher: (() => void) | null = null;
let timer: number | null = null;
const elapsedSeconds = ref<number>(0);

function formatTime(second: number): string {
  let min = Math.floor(second / 60);
  let hour = Math.floor(min / 60);

  const pad = (num: number) => String(num).padStart(2, "0");

  if (hour === 0) {
    return `${pad(min)}:${pad(second % 60)}`;
  }

  return `${hour}:${pad(min % 60)}:${pad(second % 60)}`;
}

onMounted(() => {
  if (callStore.currentCallState == null) return;
  const userId =
    callStore.currentCallState.callerId == userStore.user.id
      ? callStore.currentCallState.calleeId
      : callStore.currentCallState.callerId;

  userData.value = friendStore.friends[userId];

  watch(callStore.currentCallState, () => {
    if (
      callStore.currentCallState?.callStatus != "accepted" ||
      !callStore.currentCallState.startTime
    )
      return;

    timer = setInterval(() => {
      if (!callStore.currentCallState?.startTime) return;
      elapsedSeconds.value = Math.floor(
        (Date.now() -
          new Date(callStore.currentCallState.startTime).getTime()) /
          1000
      );
    }, 1000);
  });
});

onMounted(() => {
  // whenever remoteStream changes, attach it to the <audio>
  cleanupWatcher = watch(
    () => callStore.remoteStream,
    (stream) => {
      if (stream && audioElement.value) {
        audioElement.value.srcObject = stream;
        audioElement.value
          .play()
          .catch((err) => console.error("Audio play error:", err));
      }
    },
    { immediate: true }
  );
});

onBeforeUnmount(() => {
  if (cleanupWatcher) cleanupWatcher();

  if (timer) {
    clearInterval(timer);
    timer = null;
  }

  // Optional: stop all tracks when leaving
  callStore.remoteStream?.getTracks().forEach((t) => t.stop());
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
      <div class="w-4/5 h-auto m-3 flex flex-col items-center justify-center">
        <span class="text-xl font-semibold">{{ userData?.fullName }} </span>
        <span
          class="my-3 text-xs font-medium"
          v-if="callStore.currentCallState?.callStatus == 'calling'"
          >CALLING</span
        >
        <span
          class="my-3 text-xs font-medium"
          v-if="callStore.currentCallState?.callStatus == 'ringing'"
          >RINGING</span
        >
        <span
          class="my-3 text-xs font-medium"
          v-if="callStore.currentCallState?.callStatus == 'incoming'"
          >INCOMING</span
        >
        <span class="my-3 text-xs font-medium" v-else>{{
          formatTime(elapsedSeconds)
        }}</span>
        <audio ref="audioElement" autoplay playsinline></audio>
        <div class="w-3/4 h-auto aspect-square rounded-full overflow-hidden">
          <img :src="userData?.profilePicUrl ?? undefined" alt="" />
        </div>
      </div>
    </div>
    <div
      class="w-full h-16 flex items-center justify-around"
      v-if="callStore.currentCallState?.callStatus == 'incoming'"
    >
      <button
        class="h-3/4 w-auto aspect-square rounded-full flex items-center justify-center cursor-pointer duration-200 bg-green-500 text-color-white"
        @click="callStore.acceptCall()"
        @touchend="callStore.acceptCall()"
      >
        <IconCall :size="40" />
      </button>
      <button
        class="h-3/4 w-auto aspect-square rounded-full flex items-center justify-center cursor-pointer duration-200 bg-red-500 text-color-white"
        @click="callStore.hangup(callStore.currentCallState.callId!)"
        @touchend="callStore.hangup(callStore.currentCallState.callId!)"
      >
        <IconCall :size="40" :rotate="135" />
      </button>
    </div>
    <div class="w-full h-16 flex items-center justify-around" v-else>
      <button
        class="h-3/4 w-auto aspect-square rounded-full flex items-center justify-center cursor-pointer duration-200 hover:bg-color-background-mute"
      >
        <IconSpeaker :size="40" />
      </button>
      <button
        class="h-3/4 w-auto aspect-square rounded-full flex items-center justify-center cursor-pointer duration-200 hover:bg-color-background-mute"
        @click="unMute = callStore.alterAudioStream()"
      >
        <IconMic v-if="unMute" :size="40" />
        <IconMicOff v-else :size="40" />
      </button>
      <button
        class="h-3/4 w-auto aspect-square rounded-full flex items-center justify-center cursor-pointer duration-200 bg-red-500 text-color-white"
        @click="callStore.hangup(callStore.currentCallState?.callId!)"
        @touchend="callStore.hangup(callStore.currentCallState?.callId!)"
      >
        <IconCall :size="40" :rotate="135" />
      </button>
    </div>
  </div>
</template>
