import { defineStore } from "pinia";
import { ref } from "vue";
import { useAuthStore } from "./auth";
import { indexedDbService } from "@/services/indexDbServices";
import { mapResponseToUser, type User } from "@/types/User";
import { useUserStore } from "./user";
import type { Conversation } from "@/types/Conversation";
import { mapResponseToMessage, type Message } from "@/types/Message";
import type {
  FriendRequest,
  profileMedia,
  profileMediaUrls,
} from "@/types/Commons";

export const useFriendStore = defineStore("friend", () => {
  const friends = ref<Record<string, User>>({});
  const friendRequests = ref<FriendRequest[]>([]);

  const lastFriendsUpdate = localStorage.getItem("lastUpdated");

  const userStore = useUserStore();
  const authStore = useAuthStore();

  const { isOnline, setOnline, setOffline } =
    userStore.useOnlineStatusManager();

  async function listFriend() {
    try {
      // Get cached friend records from IndexedDB
      const result: User[] = (await indexedDbService.getAllRecords(
        "friends"
      )) as User[];

      let friends_list: User[] = result;

      // Create blob urls for user profile and banner
      if (friends_list) {
        await Promise.all(
          friends_list.map(async (user: User) => {
            // Retrive blob object from indesedDB and create there urls
            const profileMeida = (await indexedDbService.getRecord(
              "profileMedia",
              user.id
            )) as profileMedia;

            if (!profileMeida) return;
            // TODO: errors needed to bo addressed
            user.profilePicUrl = profileMeida.avatar
              ? URL.createObjectURL(profileMeida.avatar)
              : null;
            user.banner = profileMeida.banner
              ? URL.createObjectURL(profileMeida.banner)
              : null;
          })
        );
      }

      let url = "friends/get-friends";

      // Add the lastupdated date
      if (lastFriendsUpdate) {
        url += `?updateAfter=${lastFriendsUpdate}`;
      }

      // Retrive new data from server
      const response = await authStore.authAxios({
        method: "get",
        url: url,
      });

      if (response.status === 200) {
        // Create and store blob images in IndexedDB
        const updatedFriend: User[] = await Promise.all(
          response.data.map(async (data: object) => {
            // Convert raw response data to a User object.
            const user = mapResponseToUser(data);
            // Update the user record in IndexedDB.
            await indexedDbService.updateRecord("friends", user);

            const mediaUrls = await storeProfileMediaBlob(user.id, {
              avatar: user.profilePicUrl,
              banner: user.banner,
            });
            if (mediaUrls) {
              user.profilePicUrl = mediaUrls!.avatar;
              user.banner = mediaUrls!.banner;
            }
            return user;
          })
        );

        // Update the last updated timestamp.
        if (updatedFriend.length > 0) {
          friends_list.push(...updatedFriend);
          localStorage.setItem("lastUpdated", new Date().toISOString());
        }
      }

      // Store the friends list in fiends Record
      friends.value = friends_list.reduce((acc, user) => {
        acc[user.id] = user;
        return acc;
      }, {} as Record<string, User>);
    } catch (error) {
      console.error(error);
    }
  }

  async function getConversation(userId: string): Promise<Message[] | null> {
    //checking in local database
    const conversation: Conversation = (await indexedDbService.getRecord(
      "conversation",
      null,
      { participant: userId }
    )) as Conversation;

    // If conversation in local database
    if (conversation) {
      if (
        userStore.currentConversation?.receiverId == conversation.participant
      ) {
        userStore.currentConversation!.convId = conversation.id;
      }

      const request = indexedDbService.getAllRecords(
        "message",
        "conversationId",
        IDBKeyRange.only(conversation.id as string)
      );
      const oldMessages = (await request) as Message[];
      return oldMessages;
    } else {
      try {
        //retrive from server
        const response = await authStore.authAxios({
          method: "get",
          url: `conversations/get-conversation?friend_id=${userId}`,
          withCredentials: true,
        });

        if (response.status == 200) {
          const convResponse: Conversation = {
            id: response.data.id,
            participant: response.data.participants.find(
              (id: string) => id != userStore.user.id
            ) as string, //It shoud be participants
            startDate: response.data.start_date,
            lastMessageDate: response.data.last_message_date,
          };

          //Add the conversation to indesedDb and to local variable
          await indexedDbService.addRecord("conversation", convResponse);
          if (
            userStore.currentConversation?.receiverId ==
            convResponse.participant
          ) {
            userStore.currentConversation!.convId = convResponse.id;
          }

          //add the messages to the indesedDb
          const oldMessages = response.data.messages.map((msg: object) =>
            mapResponseToMessage(msg)
          );

          indexedDbService.batchUpsert("message", oldMessages);

          return oldMessages;
        }
        return null;
      } catch (error) {
        console.error(error);
        return null;
      }
    }
  }

  async function getInitialOnlineStatus() {
    try {
      // Make a GET request to fetch the list of online users
      const response = await authStore.authAxios({
        method: "get",
        url: "conversations/online-users",
      });

      if (response.status === 200) {
        // Mark all friends as online
        for (const userId of response.data.online_friends) {
          setOnline(userId);
        }
      } else {
        console.warn("Unexpected response format or status:", response);
      }
    } catch (error) {
      console.error("Failed to fetch online friend : ", error);
    }
  }

  /**
   * Fetches the avatar and banner media URLs for a given friend ID.
   * Downloads the media from secure URLs, converts them to object URLs,
   * stores the original blobs in IndexedDB, and returns media preview URLs.
   *
   * @param id - The friend's unique identifier
   * @param data - profileMediaUrls which contain aws presigned urls
   * @returns An object containing avatar and banner preview URLs (or null values), or undefined if the call fails
   */
  async function storeProfileMediaBlob(
    id: string,
    data: profileMediaUrls
  ): Promise<profileMediaUrls | null> {
    if (data.avatar == null && data.banner == null) return null;

    try {
      // Stores the actual binary blobs for IndexedDB
      const profileMediaData: profileMedia = { id, avatar: null, banner: null };

      const mediaUrls: profileMediaUrls = { avatar: null, banner: null };

      const fetchAndProcess = async (key: keyof profileMediaUrls) => {
        const mediaUrl = data[key];
        if (!mediaUrl) return null;

        const imageResponse = await fetch(mediaUrl);
        const blob = await imageResponse.blob();
        console.log(imageResponse);
        profileMediaData[key] = blob;
        mediaUrls[key] = URL.createObjectURL(blob);
      };

      // Parallel fetch avatar and banner
      await Promise.all([fetchAndProcess("avatar"), fetchAndProcess("banner")]);

      // Store the media blobs in IndexedDB
      await indexedDbService.updateRecord("profileMedia", profileMediaData);

      return mediaUrls;
    } catch (error) {
      console.error(`failed to process profile media for friend ${id}:`, error);
      return null;
    }
  }

  async function addFriend(document_id: string) {
    const user_response = await authStore.authAxios({
      method: "get",
      url: `friends/ger-friend/${document_id}`,
    });
    if (user_response.status === 200) {
      const friend = mapResponseToUser(user_response.data);

      await indexedDbService.addRecord("friends", friend);
      friends.value[friend.id] = friend;
    }
  }

  async function getPendingFriendRequests() {
    const response = await authStore.authAxios({
      method: "get",
      url: "friends/get-requests",
    });

    if (response.status === 200) {
      friendRequests.value.push(...response.data);
    }
  }

  return {
    friends,
    friendRequests,
    getConversation,
    listFriend,
    getInitialOnlineStatus,
    addFriend,
    getPendingFriendRequests,
    storeProfileMediaBlob,
  };
});
