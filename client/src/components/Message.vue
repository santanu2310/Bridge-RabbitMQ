<script setup lang="ts">
import { onMounted, ref, onUnmounted } from "vue";
import { vElementVisibility } from "@vueuse/components";
import type { Message } from "@/types/Message";
import { FileStatus } from "@/types/Commons";
import { useSyncStore } from "@/stores/background_sync";
import { useMessageStore } from "@/stores/message";
import IconDoubleTick from "./icons/IconDoubleTick.vue";
import IconAdd from "./icons/IconAdd.vue";
import IconDownload from "./icons/IconDownload.vue";
import IconUpload from "./icons/IconUpload.vue";
import IconClock from "./icons/IconClock.vue";
import IconBuffer from "./icons/IconBuffer.vue";
import IconLoading from "./icons/IconLoading.vue";
import { formatFileSize } from "@/utils/StringUtils";

interface Props {
  message: Message;
  userId: string;
}

const syncStore = useSyncStore();
const messageStore = useMessageStore();

const props = defineProps<Props>();
const messageDate = new Date(props.message.sendingTime as string);
const fileState = ref<FileStatus>(FileStatus.unsucessfull);
const progress = ref<number>(0);

const uploadEmitter = messageStore.uploadEmitter;

if (props.message.status != "pending") fileState.value = FileStatus.successfull;

const handleUploadPreprocessing = (id: string) => {
  if (id == props.message.id) {
    fileState.value = FileStatus.preProcessing;
  }
};

const handleUploadProgress = (id: string, percentCompleted: number) => {
  if (id == props.message.id) {
    fileState.value = FileStatus.uploading;
    progress.value = percentCompleted;
  }
};

const handleUploadPostProcessing = (id: string) => {
  if (id == props.message.id) {
    fileState.value = FileStatus.postProcessing;
  }
};

const handleUploadError = (id: string) => {
  if (id == props.message.id) {
    fileState.value = FileStatus.unsucessfull;
  }
};
onMounted(() => {
  if (!props.message.attachment || props.message.status != "pending") return;

  uploadEmitter.on("uploadPreprocessing", handleUploadPreprocessing);
  uploadEmitter.on("uploadProgress", handleUploadProgress);
  uploadEmitter.on("uploadPostProcessing", handleUploadPostProcessing);
  uploadEmitter.on("uploadError", handleUploadError);

  onUnmounted(() => {
    uploadEmitter.off("uploadPreprocessing", handleUploadPreprocessing);
    uploadEmitter.off("uploadProgress", handleUploadProgress);
    uploadEmitter.off("uploadPostProcessing", handleUploadPostProcessing);
    uploadEmitter.off("uploadError", handleUploadError);
  });
});

function onElementVisibility(state: boolean) {
  // This function will trigger when message is visible in the screen
  if (
    props.message.senderId != props.userId &&
    props.message.status != "seen" &&
    state
  ) {
    console.log("form message.vue", props.message);
    syncStore.markMessageAsSeen(props.message);
  }
}
</script>
<template>
  <div
    class="w-fit h-fit p-1 bg-color-background rounded-md"
    v-element-visibility="onElementVisibility"
  >
    <div
      class="min-w-56 max-w-80 w-fit p-2 flex items-center"
      v-if="message.attachment"
    >
      <div class="h-fit flex flex-grow">
        <div
          class="h-11 aspect-square flex items-center justify-center rounded-full bg-color-background-mute"
        >
          <IconAdd :size="60" />
        </div>
        <div class="ml-2 flex flex-grow flex-col">
          <span class="w-auto text-sm font-normal break-all">{{
            message.attachment.name
          }}</span>
          <span class="mt-1 text-xxs font-extralight">{{
            formatFileSize(message.attachment.size!)
          }}</span>
        </div>
      </div>

      <button
        class="h-10 aspect-square ml-3 flex justify-center items-center"
        @click="messageStore.downloadFile(message.attachment)"
        v-if="message.status != 'pending'"
      >
        <IconDownload />
      </button>
      <div class="" v-else>
        <button
          class="h-10 aspect-square ml-3 flex justify-center items-center"
          @click="messageStore.sendMessageWithFile(message)"
          v-if="fileState == FileStatus.unsucessfull"
        >
          <IconUpload />
        </button>
        <button
          class="h-10 aspect-square ml-3 flex justify-center items-center"
          v-else-if="fileState == FileStatus.uploading"
        >
          <IconLoading :progress="progress" />
        </button>
        <button
          class="h-10 aspect-square ml-3 flex justify-center items-center"
          v-else
        >
          <IconBuffer />
        </button>
      </div>
    </div>
    <div class="w-full flex flex-nowrap items-end">
      <div class="w-auto mx-1 flex-grow">
        <span class="w-auto text-base text-color-heading break-words">{{
          message.message
        }}</span>
      </div>
      <div class="w-auto h-fit mt-2 ml-2 leading-4">
        <span class="text-xxs font-thin">
          {{ messageDate.getHours() }}:{{
            messageDate.getMinutes().toString().padStart(2, "0")
          }}
        </span>
      </div>
      <div
        class="w-auto h-4 aspect-square ml-1 mt-3"
        v-if="props.message.senderId == props.userId"
      >
        <IconClock v-if="props.message.status == 'pending'" :size="90" />
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="currentColor"
          v-else-if="props.message.status == 'send'"
        >
          <path
            d="M9.9997 15.1709L19.1921 5.97852L20.6063 7.39273L9.9997 17.9993L3.63574 11.6354L5.04996 10.2212L9.9997 15.1709Z"
          ></path>
        </svg>
        <IconDoubleTick :size="100" :blue="message.status === 'seen'" v-else />
      </div>
    </div>
  </div>
</template>
