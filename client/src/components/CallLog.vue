<script setup lang="ts">
import type { CallRecord } from "@/types/Call";
import { CallStatus } from "@/types/Call";
import { useFriendStore } from "@/stores/friend";
import { useCallStore } from "@/stores/call";
import { formatDateDifference } from "@/utils/DateUtils";
import IconCall from "./icons/IconCall.vue";
import IconArrowFull from "./icons/IconArrowFull.vue";
import IconVideoCall from "./icons/IconVideoCall.vue";

const friendStore = useFriendStore();
const callStore = useCallStore();

const props = defineProps<{
  userId: string;
  callRecord: CallRecord;
}>();

// Determine which side of the call belongs to “the other person”
const friendId =
  props.callRecord.callerId == props.userId
    ? props.callRecord.calleeId
    : props.callRecord.callerId;
const friend = friendStore.friends[friendId];

function getTime(dateTime: string) {
  // Look up the friend object from the friend store using friendId
  return new Date(dateTime).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}
</script>
<template>
  <def class="w-full h-14 p-1 block">
    <div class="w-full h-full flex items-center">
      <div class="h-[80%] aspect-square mx-2 rounded-full overflow-hidden">
        <img
          class="w-full h-full object-cover"
          :src="friend.profilePicUrl ?? undefined"
          alt=""
        />
      </div>
      <div
        class="h-full flex flex-col flex-grow"
        :class="{
          'text-red-500': callRecord.status != CallStatus.ACCEPTED,
        }"
      >
        <div class="w-full h-auto text-sm font-medium">
          {{ friend.fullName }}
        </div>
        <div class="w-full h-2/5 flex">
          <div
            class="h-full"
            :class="{
              'text-green-500': callRecord.status == CallStatus.ACCEPTED,
            }"
          >
            <IconArrowFull
              v-if="props.userId == callRecord.calleeId"
              :rotate="-90"
              :size="85"
            />
            <IconArrowFull v-else :rotate="90" :size="85" />
          </div>
          <span class="text-color-heading text-xs font-light"
            >{{ formatDateDifference(callRecord.initiatedAt, false) }} at
            {{ getTime(callRecord.initiatedAt) }}</span
          >
        </div>
      </div>
      <div class="h-full w-auto aspect-square p-2">
        <button
          class="w-auto h-ful aspect-square"
          @click="
            callStore.makeCall(
              friendId,
              callRecord.callType == 'audio' ? false : true,
            )
          "
        >
          <IconCall v-if="callRecord.callType == 'audio'" />
          <IconVideoCall v-else />
        </button>
      </div>
    </div>
  </def>
</template>
