export enum MessageStatus {
  send = "send",
  received = "received",
  seen = "seen",
}

export enum SyncMessageType {
  MessageStatus = "message_status",
}

export interface MessageEvent {
  message_id: string;
  timestamp: string;
}

export interface MessageStatusUpdate {
  type: SyncMessageType.MessageStatus;
  data: MessageEvent[];
  status: MessageStatus;
}

interface BaseWebRTCMessage {
  sender_id: string;
  receiver_id: string;
  audio: boolean;
  video: boolean;
  timestamp: string | undefined;
}

export interface WebRTCOffer extends BaseWebRTCMessage {
  type: "offer";
  call_id: string | null;
  description: RTCSessionDescriptionInit;
}

export interface WebRTCAnswer extends BaseWebRTCMessage {
  type: "answer";
  call_id: string;
  description: RTCSessionDescriptionInit;
}

export interface WebRTCIceCandidate
  extends Omit<BaseWebRTCMessage, "audio" | "video"> {
  type: "ice-candidate";
  candidate: RTCIceCandidateInit;
}

export interface CallEndPayload {
  type: "user_hangup";
  call_id: string;
  ended_at: string | undefined;
  reason:
    | "hang_up"
    | "rejected"
    | "missed"
    | "network_error"
    | "busy"
    | "timeout";
  ended_by: string;
}

export interface CallStatusUpdate {
  type: "status_update";
  call_id: string;
  status: "ringing" | "calling";
  timestamp: string;
}

export type WebRTCMessage =
  | WebRTCOffer
  | WebRTCAnswer
  | WebRTCIceCandidate
  | CallEndPayload
  | CallStatusUpdate;

export type SyncMessage = WebRTCMessage | MessageStatusUpdate;
