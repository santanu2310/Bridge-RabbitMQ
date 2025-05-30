export enum CallStatus {
  CALLING = "calling",
  RINGING = "ringing",
  ACCEPTED = "accepted",
  REJECTED = "rejected",
  MISSED = "missed",
}

export interface CallRecord {
  callId: string;
  callerId: string;
  calleeId: string;
  callType: string;
  status: CallStatus;
  initiatedAt: string;
  startedAt: string | null;
  endedAt: string;
}

export function mapResponseToCallRecord(record: any): CallRecord {
  return {
    callId: record.call_id,
    callerId: record.caller_id,
    calleeId: record.callee_id,
    callType: record.call_type,
    status: record.status,
    initiatedAt: record.initiated_at,
    startedAt: record.started_at,
    endedAt: record.ended_at,
  };
}
