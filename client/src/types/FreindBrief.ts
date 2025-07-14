export interface FriendBrief {
  id: string;
  userName: string;
  fullName: string;
  bio: string | null;
  profilePicture: string | null;
  friendStatus: string | null;
}

export function mapResponseToUserBrief(user: any): FriendBrief {
  return {
  id: user.id,
  userName: user.username,
  fullName: user.full_name,
  bio: user.bio,
  profilePicture: user.profile_picture,
  friendStatus: user.friend_status ,
  };
}