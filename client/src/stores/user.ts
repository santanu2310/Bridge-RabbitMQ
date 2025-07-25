import { defineStore } from "pinia";
import { reactive, ref } from "vue";
import { useAuthStore } from "@/stores/auth";
import type { User } from "@/types/User";
import type { Message } from "@/types/Message";
import type { callState } from "@/types/Commons";

export const useUserStore = defineStore("user", () => {
  const authStore = useAuthStore();

  // Reactive object to track conversation
  const conversations = ref<{
    [key: string]: {
      messages: Message[];
      participant: string;
      lastMessageDate: string;
      isActive: boolean;
    };
  }>({});

  // Reactive object to track open chats
  const currentConversation = ref<{
    convId: string | null;
    receiverId: string | null;
  } | null>(null);

  const currentCallState = ref<callState | null>(null);
  // Reactive object to track user online status
  const userStatuses = ref<Record<string, boolean>>({});
  const isChatVisible = ref<boolean>(false);

  const user = reactive<User>({
    id: "",
    userName: "",
    fullName: "",
    email: "",
    bio: null,
    location: null,
    profilePicUrl: null,
    banner: null,
    joinedDate: "",
  });

  async function getUser() {
    try {
      const response = await authStore.authAxios({
        method: "get",
        url: "users/me",
      });

      if (response.status === 200) {
        user.id = response.data.id;
        user.userName = response.data.username;
        user.fullName = response.data.full_name;
        user.email = response.data.email;
        user.bio = response.data.bio;
        user.location = response.data.location;
        user.profilePicUrl = await getProfileBlobUrl(
          response.data.profile_picture
        );
        user.banner = await getProfileBlobUrl(response.data.banner_picture);
        user.joinedDate = response.data.created_at;
      }
    } catch (error) {
      authStore.isAuthenticated = false;
      authStore.isLoading = false;
      console.error(error);
    }
  }

  function useOnlineStatusManager() {
    return {
      // Check if user is online
      isOnline: (userId: string) => {
        return userStatuses.value[userId] || false;
      },

      // Set a user as online
      setOnline: (userId: string) => {
        userStatuses.value[userId] = true;
      },

      // Set a user as offline
      setOffline: (userId: string) => {
        userStatuses.value[userId] = false;
      },
    };
  }

  async function getProfileUrl(key: string | null): Promise<string | null> {
    if (key == null) return null;

    const response = await authStore.authAxios({
      method: "get",
      url: `users/download-url?key=${key}`,
    });

    if (response.status === 200) return response.data;

    return null;
  }

  async function getProfileBlobUrl(url: string | null): Promise<string | null> {
    const s3_url = await getProfileUrl(url);
    if (s3_url == null) return null;
    const imageResponse = await fetch(s3_url);
    const blob = await imageResponse.blob();
    return URL.createObjectURL(blob);
  }

  return {
    user,
    conversations,
    currentConversation,
    currentCallState,
    isChatVisible,
    getUser,
    useOnlineStatusManager,
    getProfileUrl,
  };
});
