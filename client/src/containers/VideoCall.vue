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

const localVideoElement = ref<HTMLVideoElement | null>(null);
const remoteVideoElement = ref<HTMLVideoElement | null>(null);

const unMute = ref<boolean>(true);
const elapsedSeconds = ref<number>(0);
const callAccepted = ref<boolean>(false);

let cleanupWatcher: (() => void) | null = null;
let timer: number | null = null;

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

  console.log(userData);

  watch(callStore.currentCallState, () => {
    if (
      callStore.currentCallState?.callStatus != "accepted" ||
      !callStore.currentCallState.startTime
    )
      return;

    callAccepted.value = true;
    timer = setInterval(() => {
      if (!callStore.currentCallState?.startTime) return;
      elapsedSeconds.value = Math.floor(
        (Date.now() -
          new Date(callStore.currentCallState.startTime).getTime()) /
          1000,
      );
    }, 1000);
  });
});

onMounted(() => {
  // whenever remoteStream changes, attach it to the <audio>
  cleanupWatcher = watch(
    () => callStore.remoteStream,
    async (stream) => {
      if (stream && remoteVideoElement.value) {
        remoteVideoElement.value.srcObject = stream;
        await remoteVideoElement.value
          .play()
          .catch((err) => console.error("Audio play error:", err));
      }
    },
    { immediate: true },
  );
  watch(
    () => callStore.localStream,
    async (stream) => {
      if (stream && localVideoElement.value) {
        localVideoElement.value.srcObject = stream;
        try {
          await localVideoElement.value.play();
        } catch (err) {
          console.warn("Local video play error:", err);
        }
      }
    },
    { immediate: true },
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
      class="h-auto m-2 rounded-xl flex flex-grow bg-color-background-soft relative"
    >
      <div
        class="w-1.2 h-auto flex flex-col items-center justify-center absolute left-1/2 -translate-x-1/2 bg-transparent z-10"
      >
        <span class="text-base font-semibold">{{ userData?.fullName }} </span>
        <span
          class="my-1 text-xs font-normal"
          v-if="callStore.currentCallState?.callStatus == 'calling'"
          >CALLING</span
        >
        <span
          class="my-1 text-xs font-normal"
          v-if="callStore.currentCallState?.callStatus == 'ringing'"
          >RINGING</span
        >
        <span
          class="my-1 text-xs font-normal"
          v-if="callStore.currentCallState?.callStatus == 'incoming'"
          >INCOMING</span
        >
        <span class="my-1 text-xs font-normal" v-if="callAccepted">{{
          formatTime(elapsedSeconds)
        }}</span>
        <div
          class="w-1/3 h-auto aspect-square rounded-full mt-2 overflow-hidden"
          v-else
        >
          <img :src="userData?.profilePicUrl ?? undefined" alt="" />
        </div>
      </div>
      <div class="w-full h-full">
        <video
          class="w-full h-full object-cover"
          ref="remoteVideoElement"
          autoplay
          playsinline
        ></video>
      </div>
      <div
        class="w-28 h-48 absolute bottom-5 right-5 transition duration-1000"
        :class="{ calling: !callAccepted }"
      >
        <video
          class="w-full h-full object-cover"
          ref="localVideoElement"
          autoplay
          muted
          playsinline
        ></video>
      </div>
    </div>

    <div
      class="w-full h-16 flex items-center justify-around"
      v-if="callStore.currentCallState?.callStatus == 'incoming'"
    >
      <button
        class="h-3/4 w-auto aspect-square rounded-full flex items-center justify-center cursor-pointer duration-200 bg-green-500 text-color-white"
        @click="callStore.acceptCall()"
      >
        <IconCall :size="40" />
      </button>
      <button
        class="h-3/4 w-auto aspect-square rounded-full flex items-center justify-center cursor-pointer duration-200 bg-red-500 text-color-white"
        @click="callStore.hangup(callStore.currentCallState.callId!)"
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
      >
        <IconCall :size="40" :rotate="135" />
      </button>
    </div>
  </div>
</template>
<style lang="css" scoped>
.calling {
  width: 100%;
  height: 100%;
  top: 0;
  left: 0;
}
</style>
