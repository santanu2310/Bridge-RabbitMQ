<script setup lang="ts">
import IconCall from "@/components/icons/IconCall.vue";
import IconMic from "@/components/icons/IconMic.vue";
import IconMicOff from "@/components/icons/IconMicOff.vue";
import IconVideoCall from "@/components/icons/IconVideoCall.vue";
import IconVideoOff from "@/components/icons/IconVideoOff.vue";
import IconArrow from "@/components/icons/IconArrow.vue";
import type { User } from "@/types/User";
import { useCallStore } from "@/stores/call";
import { useFriendStore } from "@/stores/friend";
import { useUserStore } from "@/stores/user";
import { ref, computed, watch, onMounted, onBeforeUnmount } from "vue";

const callStore = useCallStore();
const friendStore = useFriendStore();
const userStore = useUserStore();

const userData = ref<User | null>(null);

const localVideoElement = ref<HTMLVideoElement | null>(null);
const remoteVideoElement = ref<HTMLVideoElement | null>(null);
const callUI = ref<HTMLElement | null>(null);

const unMute = ref<boolean>(true);
const video = ref<boolean>(true);
const controlsVisible = ref<boolean>(true);
const callAccepted = ref<boolean>(false);

const elapsedSeconds = ref<number>(0);
const callTimer = ref<number | null>(null);

const hideTimeout = ref<number | null>(4);
const countdownInterval = ref<number | null>(null);
let isTouch = "ontouchend" in window;

// Cleanup functions
let watchers: (() => void)[] = [];

// Get the userId who is either calling or being called
const otherUserId = computed(() => {
  if (!callStore.currentCallState) return null;
  return callStore.currentCallState.callerId === userStore.user.id
    ? callStore.currentCallState.calleeId
    : callStore.currentCallState.callerId;
});

// For the UI elements

function showControls() {
  controlsVisible.value = true;
  resetTimer();
}

function hideControls() {
  clearTimeout(hideTimeout.value!);
  if (callAccepted) controlsVisible.value = false;
}

function resetTimer() {
  if (!hideTimeout.value) return;
  clearTimeout(hideTimeout.value);

  hideTimeout.value = setTimeout(() => {
    hideControls();
  }, 4000);
}

function clearAllTimeouts() {
  if (hideTimeout.value) {
    clearTimeout(hideTimeout.value);
    hideTimeout.value = null;
  }
  if (countdownInterval.value) {
    clearInterval(countdownInterval.value);
    countdownInterval.value = null;
  }
  if (callTimer.value) {
    clearInterval(callTimer.value);
    callTimer.value = null;
  }
}

// Format seconds into a readable time string
function formatTime(second: number): string {
  let min = Math.floor(second / 60);
  let hour = Math.floor(min / 60);

  const pad = (num: number) => String(num).padStart(2, "0");

  if (hour === 0) {
    return `${pad(min)}:${pad(second % 60)}`;
  }

  return `${hour}:${pad(min % 60)}:${pad(second % 60)}`;
}

// Attach media stream to the video element (plays the video stream)
async function attachStreamToVideo(
  stream: MediaStream | null,
  videoElement: HTMLVideoElement | null,
  isLocal = false
) {
  if (!stream || !videoElement) return;

  try {
    videoElement.srcObject = stream;
    await videoElement.play();
  } catch (err) {
    console.error(`${isLocal ? "Local" : "Remote"} video play error:`, err);
  }
}

// Setup event listeners for showing/hiding controls based on user interaction
function setupEventListeners() {
  if (!callUI.value) return;

  const element = callUI.value;

  if (isTouch) {
    const touchHandler = (e: TouchEvent) => {
      e.preventDefault();
      showControls();
    };
    element.addEventListener("touchend", touchHandler);
    element.addEventListener("touchmove", touchHandler);

    // Cleanup function to remove touch listeners
    return () => {
      element.removeEventListener("touchend", touchHandler);
      element.removeEventListener("touchmove", touchHandler);
    };
  } else {
    // For mouse devices: show/hide controls on hover/mouse movement
    element.addEventListener("mouseenter", showControls);
    element.addEventListener("mouseleave", hideControls);
    element.addEventListener("mousemove", showControls);

    // Cleanup function to remove mouse event listeners
    return () => {
      element.removeEventListener("mouseenter", showControls);
      element.removeEventListener("mouseleave", hideControls);
      element.removeEventListener("mousemove", showControls);
    };
  }
}

// Setup watchers to listen for stream changes and attach them to video elements
function setupStreamWatchers() {
  // Watch for changes in remote stream
  const remoteWatcher = watch(
    () => callStore.remoteStream,
    (stream) => attachStreamToVideo(stream, remoteVideoElement.value, false)
  );

  // Watch for changes in local stream
  const localWatcher = watch(
    () => callStore.localStream,
    (stream) => attachStreamToVideo(stream, localVideoElement.value, true)
  );

  return [remoteWatcher, localWatcher];
}

// Watch call state changes to update UI and start call timer after acceptance
function setupCallStateWatcher() {
  return watch(
    () => callStore.currentCallState,
    (callState) => {
      console.log("current call state ", callStore.currentCallState);
      if (!callState) return;
      if (callState.callStatus != "accepted" || !callState.startTime) return;

      // Update user data
      if (otherUserId.value && friendStore.friends[otherUserId.value]) {
        userData.value = friendStore.friends[otherUserId.value];
      }

      // Start the call timer
      callAccepted.value = true;
      callTimer.value = setInterval(() => {
        if (!callState.startTime) return;
        elapsedSeconds.value = Math.floor(
          (Date.now() - new Date(callState.startTime).getTime()) / 1000
        );
      }, 1000);
    },
    { immediate: true, deep: true }
  );
}

onMounted(() => {
  const eventCleanup = setupEventListeners();
  if (eventCleanup) {
    watchers.push(eventCleanup);
  }
  // Setup watchers
  const streamWatchers = setupStreamWatchers();
  const callStateWatcher = setupCallStateWatcher();

  console.log("call accepted ", callAccepted.value);

  watchers.push(...streamWatchers, callStateWatcher);
});

onBeforeUnmount(() => {
  // Clean up all watchers and event listeners
  watchers.forEach((cleanup) => cleanup());
  watchers = [];

  clearAllTimeouts();

  callStore.remoteStream?.getTracks().forEach((t) => t.stop());
  callStore.localStream?.getTracks().forEach((t) => t.stop());
});
</script>
<template>
  <div class="w-full max-w-[1024px] h-full flex flex-col relative" ref="callUI">
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
        v-if="controlsVisible"
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
        :class="{ calling: !callAccepted, 'bottom-20': controlsVisible }"
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
        type="button"
        class="h-3/4 w-auto aspect-square rounded-full flex items-center justify-center cursor-pointer duration-200 bg-green-500 text-color-white"
        @click="callStore.acceptCall()"
        @touchend="callStore.acceptCall()"
      >
        <IconCall :size="40" />
      </button>
      <button
        type="button"
        class="h-3/4 w-auto aspect-square rounded-full flex items-center justify-center cursor-pointer duration-200 bg-red-500 text-color-white"
        @click="callStore.hangup(callStore.currentCallState.callId!)"
        @touchend="callStore.hangup(callStore.currentCallState.callId!)"
      >
        <IconCall :size="40" :rotate="135" />
      </button>
    </div>
    <div
      class="w-full h-16 flex items-center justify-around absolute bottom-5 left-0 bg-transparent"
      v-else-if="controlsVisible"
    >
      <button
        class="h-3/4 w-auto aspect-square rounded-full flex items-center justify-center cursor-pointer duration-200 hover:bg-color-background-mute"
        @click="video = callStore.alterVideoStream()"
        @touchend="video = callStore.alterVideoStream()"
      >
        <IconVideoCall :size="40" v-if="video" />
        <IconVideoOff :size="40" v-else />
      </button>
      <button
        class="h-3/4 w-auto aspect-square rounded-full flex items-center justify-center cursor-pointer duration-200 hover:bg-color-background-mute"
        @click="unMute = callStore.alterAudioStream()"
        @touchend="unMute = callStore.alterAudioStream()"
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
<style lang="css" scoped>
.calling {
  width: 100%;
  height: 100%;
  top: 0;
  left: 0;
}
</style>
