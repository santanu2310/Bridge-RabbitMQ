import { indexedDbService } from "@/services/indexDbServices";
import type { Message } from "@/types/Message";
import type { Conversation } from "@/types/Conversation";
import { useUserStore } from "../user";
import { useAuthStore } from "../auth";
import { useSyncStore } from "../background_sync";
import { addMessageInState, updateMessageInState } from "@/utils/MessageUtils";
import {
  MessageStatus,
  SyncMessageType,
  type MessageStatusUpdate,
} from "@/types/SocketEvents";

// --- helpers ---
function isValidMessage(msg: any): boolean {
  return (
    msg.id &&
    msg.conversation_id &&
    msg.sender_id &&
    msg.message != null &&
    msg.sending_time &&
    msg.status
  );
}

async function saveMessageToDB(message: Message) {
  await indexedDbService.addRecord("message", message);
}

async function handleNewConversation(message: Message) {
  const userStore = useUserStore();
  const authStore = useAuthStore();

  const response = await authStore.authAxios({
    method: "get",
    url: "/conversations/get-conversation",
    params: {
      conversation_id: message.conversationId,
    },
  });

  if (response.status == 200) {
    const convResponse: Conversation = {
      id: response.data.id,
      participant: response.data.participants.find(
        (id: string) => id != userStore.user.id,
      ) as string, //It shoud be participants
      startDate: response.data.start_date,
      lastMessageDate: response.data.last_message_date,
    };

    //Add the conversation to indesedDb and to local variable
    await indexedDbService.addRecord("conversation", convResponse);
    if (userStore.currentConversation?.receiverId == convResponse.participant) {
      userStore.currentConversation!.convId = convResponse.id;
    }
    userStore.conversations[convResponse.id as string] = {
      isActive: true,
      messages: [],
      lastMessageDate: convResponse.lastMessageDate as string,
      participant: convResponse.participant as string,
    };
  }
  //
  // const newConversation: Conversation = {
  //   id: message.conversationId,
  //   participant: message.senderId,
  //   startDate: null,
  //   lastMessageDate: message.sendingTime,
  // };

  //
  // userStore.currentConversation!.convId = message.conversationId as string;
  //
  // console.log("conversations : ", userStore.conversations);
  //
  // await indexedDbService.addRecord("conversation", newConversation);
}

async function updateConversation(
  conversation: Conversation,
  message: Message,
  userStore: any,
) {
  userStore.conversations[message.conversationId!].lastMessageDate =
    message.sendingTime as string;

  conversation.lastMessageDate = message.sendingTime;
  await indexedDbService.updateRecord("conversation", conversation);
}

async function handleTempMessage(message: Message, msg: any) {
  if (msg.temp_id) {
    await indexedDbService.deleteRecord("message", msg.temp_id);
    updateMessageInState(message, msg.temp_id);
    await indexedDbService.deleteRecord("tempFile", msg.temp_id);
  }
}

function sendAcknowledgement(message: Message, sendMessage: Function) {
  const now = new Date().toISOString();
  const syncMessge: MessageStatusUpdate = {
    type: SyncMessageType.MessageStatus,
    data: [
      {
        message_id: message.id as string,
        timestamp: now,
      },
    ],
    status: MessageStatus.received,
  };

  sendMessage(syncMessge);
}

export {
  isValidMessage,
  saveMessageToDB,
  handleNewConversation,
  updateConversation,
  handleTempMessage,
  sendAcknowledgement,
};
