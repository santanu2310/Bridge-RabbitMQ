import { EventEmitter } from "events";
import axios from "axios";
import { useRouter } from "vue-router";
import type { PacketType, RawData, Packet } from "@/types/Commons";

type ReadyState = "opening" | "open" | "closing" | "closed";

const router = useRouter();
/**
 * The Socket class extends EventEmitter to enable event-driven behavior.
 * It wraps a WebSocket connection with additional functionality like
 * automatic reconnection, heartbeat (ping/pong), and message buffering.
 */
export class Socket extends EventEmitter {
  private url: string;
  private socket: WebSocket | null = null;
  private heartbeatInterval: number = 30000;
  private pingTimeoutTimer: number | null;
  private pingIntervalTimer: number | null;

  private pingTimeout: number = 20000;
  private pingInterval: number = 25000;
  private packetBuffer: Packet[] = [];

  // Internal tracking of the socket's state (default is "opening")
  public _readyState: ReadyState = "opening";

  /**
   * Getter to access the current ready state of the socket.
   */
  get readyState() {
    return this._readyState;
  }

  /**
   * Setter to update the current ready state of the socket.
   */
  set readyState(state: ReadyState) {
    this._readyState = state;
  }

  /**
   * Constructor initializes a Socket instance with a given URL.
   * @param url The WebSocket URL to connect to.
   */
  constructor(url: string) {
    super();
    this.url = url;
    this.pingIntervalTimer = null;
    this.pingTimeoutTimer = null;
  }

  /**
   * Establishes a WebSocket connection if not already open.
   * Also sets up event handlers for open, close, error, and message events.
   */
  connect(): void {
    if (this.readyState === "open") {
      console.warn("Socket is open.");
      return;
    }
    this.socket = new WebSocket(this.url);

    this.socket.onopen = () => {
      this.readyState = "open";
      this.flush();
      this.schedulePing();
    };

    this.socket.onclose = this.onClose.bind(this);

    this.socket.onerror = async (error: Event): Promise<void> => {
      console.error("WebSocket error:", error);
      const response = await axios({
        method: "post",
        url: import.meta.env.VITE_API_BASE + "users/refresh-token",
        withCredentials: true,
      });

      if (response.status !== 200) {
        router.push({ name: "login" });
      }
      this.emit("error", error);
    };

    this.socket.onmessage = (event: MessageEvent) => {
      if ("open" !== this.readyState) {
        console.debug("packet received with closed socket");
        return;
      }

      const data = JSON.parse(event.data);

      switch (data.type) {
        case "pong":
          if (this.pingTimeoutTimer) clearTimeout(this.pingTimeoutTimer);
          this.schedulePing();
          break;

        case "message":
          this.emit("message", data.data);
          break;

        default:
          console.warn("Unknown packet type: ", data.type);
      }
    };
  }

  /**
   * Schedule a ping message to be sent after the specified interval.
   * After sending the ping, the ping timeout is reset.
   */
  private schedulePing() {
    this.pingIntervalTimer = setTimeout(() => {
      this.sendMessage("ping");
      this.resetPingTimeout();
    }, this.pingInterval);
  }

  /**
   * Reset the ping timeout which will close the socket if a pong is not received in time.
   */
  private resetPingTimeout() {
    this.pingTimeoutTimer = setTimeout(() => {
      if (this.readyState === "closed") this.connect();
      this.socket?.close();
    }, this.pingTimeout);
  }

  /**
   * Sends a message packet with the provided raw data.
   * @param data Raw data to be sent in the message.
   * @returns The current instance to allow chaining.
   */
  public send(data: RawData) {
    this.sendMessage("message", data);
    return this;
  }

  /**
   * Constructs and sends a packet with the specified type and optional data.
   * If the socket is in closing or closed state, buffers the packet to be sent later.
   * @param type The type of the packet (e.g., "ping", "message").
   * @param data Optional data payload.
   */
  private sendMessage(type: PacketType, data?: RawData) {
    const packet: Packet = {
      type,
    };
    if (data) packet.data = data;

    if ("closing" !== this.readyState && "closed" !== this.readyState) {
      this.socket?.send(JSON.stringify(packet));
    } else {
      // Buffer the packet to send later when connection is re-established.
      this.packetBuffer.push(packet);
    }
  }

  /**
   * Handles the socket closing event. It resets state and timers,
   * logs the closure, and attempts to reconnect after a delay.
   */
  private onClose(event: CloseEvent) {
    console.error(event);
    this.readyState = "closed";
    console.info("connection is closed - Opening in 5 sec");

    if (this.pingIntervalTimer !== null) {
      clearTimeout(this.pingIntervalTimer);
      this.pingIntervalTimer = null;
    }

    if (this.pingTimeoutTimer !== null) {
      clearTimeout(this.pingTimeoutTimer);
      this.pingTimeoutTimer = null;
    }

    this.pingIntervalTimer = null;
    this.pingTimeoutTimer = null;

    setTimeout(() => {
      this.connect();
    }, 5000);
  }

  /**
   * Flushes the packet buffer by attempting to send any buffered packets now that
   * the connection has been re-established.
   */
  private flush() {
    const tempBuffer = this.packetBuffer;
    this.packetBuffer = [];

    for (const packet of tempBuffer) {
      this.sendMessage(packet.type, packet?.data);
    }
  }
}
