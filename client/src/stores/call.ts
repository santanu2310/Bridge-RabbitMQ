import { ref, watch } from "vue";
import { defineStore } from "pinia";
import { useSyncStore } from "./background_sync";
import { useUserStore } from "./user";
import { useAuthStore } from "./auth";
import type {
  WebRTCAnswer,
  WebRTCOffer,
  WebRTCIceCandidate,
  CallEndPayload,
  WebRTCMessage,
} from "@/types/SocketEvents";
import {
  type CallRecord,
  CallStatus,
  mapResponseToCallRecord,
} from "@/types/Call";
import type { callState } from "@/types/Commons";
import { indexedDbService } from "@/services/indexDbServices";

export const useCallStore = defineStore("call", () => {
  const syncStore = useSyncStore();
  const userStore = useUserStore();
  const authStore = useAuthStore();

  const socket = syncStore.socket;
  const lastCall = localStorage.getItem("lastCall");

  const currentCallState = ref<callState | null>(null);
  const callRecords = ref<CallRecord[]>([]);
  const pc = ref<RTCPeerConnection | undefined>(undefined);
  const remoteStream = ref<MediaStream | null>(null);
  const localStream = ref<MediaStream | null>(null);

  watch(currentCallState, () => {
    userStore.currentCallState = currentCallState.value;
  });
  const configuration = {
    iceServers: [
      { urls: "stun:stun.l.google.com:19302" },
      {
        urls: "turn:15.206.88.28:3478?transport=udp",
        username: "webrtcuser1",
        credential: "webrtcpassword1",
      },
    ],
  };

  socket.on("message", async (msg: WebRTCMessage) => {
    // Handle WebRTC offer message
    if (msg.type == "offer") {
      if (msg.description) {
        // Set current call state for an incoming call
        currentCallState.value = {
          callId: msg.call_id,
          callerId: msg.sender_id,
          calleeId: msg.receiver_id,
          isMuted: false,
          isCameraOn: msg.video,
          callStatus: "incoming",
          minimised: false,
          startTime: undefined,
          initiationTime: msg.timestamp,
          description: msg.description,
        };

        // Create a new RTCPeerConnection and prepare local media
        pc.value = await createRTCPeerConnection(
          configuration,
          currentCallState.value.callerId,
          currentCallState.value.isCameraOn
        );
      }

      // Handle ICE candidate message
    } else if (msg.type == "ice-candidate") {
      if (msg.candidate && pc.value) {
        try {
          await pc.value.addIceCandidate(msg.candidate);
        } catch (e) {
          console.error("Error adding received ICE candidate", e);
        }
      }

      // Handle answer message from remote peer
    } else if (msg.type == "answer") {
      if (msg.description && pc.value) {
        const remoteDesc = new RTCSessionDescription(msg.description);
        await pc.value.setRemoteDescription(remoteDesc);

        // Update call state to reflect an active call
        currentCallState.value!.callId = msg.call_id;
        currentCallState.value!.startTime = msg.timestamp;
        currentCallState.value!.callStatus = "accepted";
      }

      // Handle status update messages like ringing, calling, or accepted
    } else if (msg.type == "status_update") {
      if (!currentCallState.value?.callId) {
        currentCallState.value!.callId = msg.call_id;
      }
      if (msg.status == "ringing") {
        currentCallState.value!.callStatus = "ringing";
        currentCallState.value!.initiationTime = msg.timestamp; //TODO: assign if initiationTime is undefined
      } else if (msg.status == "calling") {
        currentCallState.value!.callStatus = "calling";
        currentCallState.value!.initiationTime = msg.timestamp;
      } else if (msg.status == "accepted") {
        currentCallState.value!.callStatus = "accepted";
        currentCallState.value!.startTime = msg.timestamp;
      }

      // Handle user hangup (end call)
    } else if (msg.type == "user_hangup") {
      let callStatus: CallStatus = CallStatus.ACCEPTED;

      if (msg.reason === "rejected") {
        callStatus = CallStatus.REJECTED;
      } else if (msg.reason === "missed") {
        callStatus = CallStatus.MISSED;
      }
      const callRecord: CallRecord = {
        id: currentCallState.value!.callId!,
        callType: currentCallState.value!.isCameraOn ? "video" : "audio",
        callerId: currentCallState.value!.callerId,
        calleeId: currentCallState.value!.calleeId,
        initiatedAt: currentCallState.value!.initiationTime!,
        startedAt: currentCallState.value?.startTime!,
        status: callStatus, //TODO: This can be undefined if user cant connect to the server.
        endedAt: msg.ended_at!,
      };

      localStorage.setItem("lastCall", msg.ended_at!);
      clearCallData();
      callRecords.value.unshift(callRecord);

      await indexedDbService.addRecord("callLog", callRecord);
    }
  });

  async function createRTCPeerConnection(
    configuration: object,
    receiverId: string,
    video: boolean = false
  ): Promise<RTCPeerConnection> {
    // Create a new RTCPeerConnection with the provided configuration
    const peerConnection = new RTCPeerConnection(configuration);

    // Get local audio stream
    try {
      localStream.value = await navigator.mediaDevices.getUserMedia({
        video: video,
        audio: true,
      });
    } catch (error) {
      console.error("Failed to access media devices" + error);
      peerConnection.close();
      throw error;
    }

    console.log(localStream.value);

    // Add local tracks to the peer connection
    localStream.value.getTracks().forEach((track) => {
      peerConnection.addTrack(track, localStream.value!);
    });

    // Create empty MediaStream for remote tracks
    const remote = new MediaStream();

    // When remote tracks are received, add them to the remote MediaStream
    peerConnection.addEventListener("track", (e) => {
      console.log("remoteStream : ", e.track);
      console.log(remoteStream.value);

      remote.addTrack(e.track);

      remoteStream.value = remote;
      console.log("remote : ", remote);
    });

    // Save the remote stream for rendering in UI
    // remoteStream.value = remote;

    // Listen for ICE candidates and send them to the remote peer
    peerConnection.addEventListener("icecandidate", (event) => {
      if (event.candidate && event.candidate.candidate !== "") {
        const iceCandidate: WebRTCIceCandidate = {
          type: "ice-candidate",
          sender_id: userStore.user.id,
          receiver_id: receiverId,
          candidate: event.candidate,
          timestamp: new Date().toISOString(),
        };
        syncStore.sendMessage(iceCandidate);
      }
    });

    //TODO: Will be used to make the connection more robust
    peerConnection.addEventListener("connectionstatechange", () => {
      console.log("Connection state:", peerConnection.connectionState);
    });

    return peerConnection;
  }

  // Initiates a WebRTC call by creating an offer and sending it to the receiver
  async function makeCall(receiverId: string, video: boolean = false) {
    // Initialize the current call state with relevant info
    currentCallState.value = {
      callId: null,
      callerId: userStore.user.id,
      calleeId: receiverId,
      isMuted: false,
      isCameraOn: video,
      callStatus: "calling",
      minimised: false,
      description: null,
      startTime: undefined,
      initiationTime: undefined,
    };

    // Create a new RTCPeerConnection and get local media stream
    pc.value = await createRTCPeerConnection(configuration, receiverId, video);

    // Create an SDP offer describing the local end of the connection
    const offer = await pc.value.createOffer();
    // Set the local description to the generated offer
    await pc.value.setLocalDescription(offer);

    // Construct the WebRTC offer payload to send over signaling channel
    const callOffer: WebRTCOffer = {
      type: "offer",
      sender_id: userStore.user.id,
      receiver_id: receiverId,
      call_id: null,
      description: offer,
      audio: true,
      video: video,
      timestamp: new Date().toISOString(),
    };

    // Send the offer to the callee
    await syncStore.sendMessage(callOffer);
  }

  // Accepts an incoming WebRTC call by setting the remote description and sending an answer
  async function acceptCall() {
    // Ensure we have a valid offer description and call ID before proceeding
    if (
      !currentCallState.value?.description ||
      !currentCallState.value.callId ||
      !pc.value
    ) {
      console.log("cant prosieed with call function");
      return;
    }
    currentCallState.value.callStatus = "accepted";
    console.log(currentCallState.value.isCameraOn);
    // // Create a new RTCPeerConnection and prepare local media
    // pc.value = await createRTCPeerConnection(
    //   configuration,
    //   currentCallState.value.callerId,
    //   currentCallState.value.isCameraOn
    // );
    // Set the received offer as the remote description
    await pc.value.setRemoteDescription(
      new RTCSessionDescription(currentCallState.value.description)
    );

    // Create an SDP answer in response to the offer
    const answer = await pc.value.createAnswer();
    // Set the local description to the generated answer
    await pc.value.setLocalDescription(answer);

    // Construct and send the answer payload to send to the caller
    const callAnswer: WebRTCAnswer = {
      type: "answer",
      sender_id: userStore.user.id,
      receiver_id: currentCallState.value.callerId,
      description: answer,
      call_id: currentCallState.value.callId,
      audio: true,
      video: currentCallState.value.isCameraOn,
      timestamp: new Date().toISOString(),
    };
    syncStore.sendMessage(callAnswer);
  }

  function clearCallData(): void {
    // Stop the local audio track
    localStream.value?.getTracks().forEach((track) => track.stop());

    pc.value?.close();
    pc.value = undefined;
    currentCallState.value = null;
  }

  // Ends an active WebRTC call by sending a hangup signal to the remote peer
  async function hangup(call_id: string): Promise<void> {
    let reason: "hang_up" | "rejected" | "missed" = "hang_up";

    if (currentCallState.value?.callStatus === "incoming") {
      reason = "rejected";
    }
    if (
      currentCallState.value?.callStatus === "calling" ||
      currentCallState.value?.callStatus === "ringing"
    ) {
      reason = "missed";
    }
    // Construct and send the payload to signal call termination
    const endPayload: CallEndPayload = {
      call_id: call_id,
      type: "user_hangup",
      ended_at: undefined,
      ended_by: userStore.user.id,
      reason: reason,
    };
    await syncStore.sendMessage(endPayload);
  }

  // Toggles the local audio stream (mute/unmute) and returns the new mute state
  function alterAudioStream(): boolean {
    if (!localStream.value) return false;

    // Get the current stete of local audio stream
    const currentState = localStream.value.getAudioTracks()[0]?.enabled ?? true;

    // Togle the stete of audio tracks
    localStream.value?.getAudioTracks().forEach((track) => {
      track.enabled = !currentState;
    });

    return !currentState;
  }

  function alterVideoStream(): boolean {
    if (!localStream.value) return false;

    // Get the current stete of local video stream
    const currentState = localStream.value.getVideoTracks()[0]?.enabled ?? true;

    // Togle the stete of video tracks
    localStream.value?.getVideoTracks().forEach((track) => {
      track.enabled = !currentState;
    });

    return !currentState;
  }
  // async function getCallRecord(call_id: string): Promise<CallRecord> {
  //   try {
  //     const response = await authStore.authAxios({
  //       method: "get",
  //       url: `call-log/${call_id}`,
  //     });
  //
  //     if (response.status !== 200)
  //       throw new Error(
  //         `Failed to fetch call record. Status: ${response.status}`,
  //       );
  //
  //     const callLog: CallRecord = mapResponseToCallRecord(response.data);
  //     return callLog;
  //   } catch (error) {
  //     console.error("Error in getCallRecord:", error);
  //     throw new Error(
  //       "Unable to retrieve call record. Please try again later.",
  //     );
  //   }
  // }
  async function loadOldRecords() {
    // Retrieve all records from the “callLog” object store, ordered by “endedAt” descending.
    // TODO: The function should accept two parameter (dateBefore and noOfRecord).
    const oldReocrds: CallRecord[] = (await indexedDbService.getAllRecords(
      "callLog",
      "endedAt",
      undefined,
      "prev"
    )) as CallRecord[];

    // Push all retrieved records into the reactive callRecords array.
    callRecords.value.push(...oldReocrds);
  }
  async function syncCallLogs() {
    try {
      // load old call records form indexedDB into memrory
      await loadOldRecords();

      // Build the API endpoint, optionally including the last sync date
      let url = "/sync/call-log";
      if (lastCall) url += `?date_after=${lastCall}`;

      // Send an authenticated GET request
      const response = await authStore.authAxios({
        method: "get",
        url: url,
      });

      // Check for a successful response
      if (response.status !== 200)
        throw new Error(
          `Failed to fetch call record. Status: ${response.status}`
        );

      // Transform the response data into CallRecord objects array
      let newLogs: CallRecord[] = [];
      for (let log of response.data) {
        newLogs.push(mapResponseToCallRecord(log));
      }

      // Prepend the new logs to the in-memory call records array
      callRecords.value.unshift(...newLogs);
      // Update the last call timestamp in local storage for the next sync
      await indexedDbService.batchUpsert("callLog", newLogs);

      if (newLogs.length > 0) {
        localStorage.setItem("lastCall", newLogs[0].endedAt);
      }
    } catch (error) {
      console.error("Error in getCallRecord:", error);
    }
  }

  return {
    callRecords,
    makeCall,
    currentCallState,
    acceptCall,
    hangup,
    remoteStream,
    localStream,
    alterAudioStream,
    alterVideoStream,
    syncCallLogs,
  };
});
