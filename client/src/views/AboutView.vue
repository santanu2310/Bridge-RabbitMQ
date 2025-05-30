<script setup lang="ts">
	function testRTC() {
		const pc = new RTCPeerConnection({
			iceServers: [
				{ urls: "stun:stun.l.google.com:19302" },
				{
					urls: "turn:15.206.88.28:3478?transport=udp",
					username: "webrtcuser1",
					credential: "webrtcpassword1",
				},
			],
		});

		pc.onicecandidate = (e) => {
			if (e.candidate) console.log(e.candidate.candidate);
		};

		pc.createDataChannel("test");
		pc.createOffer().then((offer) => pc.setLocalDescription(offer));
	}
</script>

<template>
	<button @click="testRTC()">Hello</button>
</template>
