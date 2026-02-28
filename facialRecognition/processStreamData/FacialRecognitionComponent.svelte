<script>
	import { onMount, onDestroy } from 'svelte';

	let ws = null;
	let videoElement;
	let canvas;
	let canvasContext;
	let isConnected = false;
	let registerMode = false;
	let detectionResults = null;
	let faceDetected = false;
	let frameCount = 0;
	let sendInterval = null;

	onMount(() => {
		// Setup canvas for capturing frames
		canvas = document.createElement('canvas');
		canvas.width = 640;
		canvas.height = 480;
		canvasContext = canvas.getContext('2d');

		// Connect to WebSocket
		connectWebSocket();

		// Start webcam
		startWebcam();
	});

	onDestroy(() => {
		// Cleanup
		if (ws) ws.close();
		if (sendInterval) clearInterval(sendInterval);
		if (videoElement && videoElement.srcObject) {
			videoElement.srcObject.getTracks().forEach(track => track.stop());
		}
	});

	function connectWebSocket() {
		// Detect if running on the sslip.io domain
		const hostname = window.location.hostname;
		const wsUrl = hostname.includes('sslip.io') 
			? `wss://${hostname}:8000/ws/stream`  // Use WSS (secure) for https domains
			: `ws://localhost:8000/ws/stream`;   // Use WS for localhost
		
		console.log('Connecting to WebSocket:', wsUrl);
		ws = new WebSocket(wsUrl);

		ws.onopen = () => {
			console.log('Connected to facial recognition WebSocket');
			isConnected = true;
		};

		ws.onmessage = (event) => {
			try {
				const data = JSON.parse(event.data);
				console.log('Response from server:', data);

				if (data.type === 'face_detection') {
					detectionResults = data;
					faceDetected = data.face_count > 0;
				} else if (data.type === 'registration_success') {
					alert(`✓ Face registered for ${data.name}`);
					registerMode = false;
				} else if (data.type === 'registration_error') {
					alert(`✗ Registration failed: ${data.message}`);
					registerMode = false;
				} else if (data.type === 'command_response') {
					if (data.action === 'clear') {
						alert('Database cleared');
					}
				}
			} catch (error) {
				console.error('Error parsing response:', error);
			}
		};

		ws.onerror = (error) => {
			console.error('WebSocket error:', error);
			isConnected = false;
		};

		ws.onclose = () => {
			console.log('WebSocket disconnected');
			isConnected = false;
		};
	}

	function startWebcam() {
		navigator.mediaDevices
			.getUserMedia({ video: { width: 640, height: 480 } })
			.then(stream => {
				videoElement.srcObject = stream;
				videoElement.play();

				// Start sending frames to server
				sendInterval = setInterval(() => {
					sendFrameToWebSocket();
				}, 500); // Send frame every 500ms (2 FPS)
			})
			.catch(error => {
				console.error('Error accessing webcam:', error);
				alert('Could not access webcam. Make sure to allow camera permissions.');
			});
	}

	function sendFrameToWebSocket() {
		if (!videoElement || !canvasContext || !ws || ws.readyState !== WebSocket.OPEN) {
			return;
		}

		try {
			// Draw video frame to canvas
			canvasContext.drawImage(videoElement, 0, 0, canvas.width, canvas.height);

			// Convert canvas to base64
			const imageDataUrl = canvas.toDataURL('image/jpeg', 0.8); // 0.8 = quality

			// Send to WebSocket
			ws.send(imageDataUrl);
			frameCount++;
		} catch (error) {
			console.error('Error sending frame:', error);
		}
	}

	function toggleRegister() {
		registerMode = !registerMode;
		if (registerMode) {
			// Send register command
			ws.send(JSON.stringify({ action: 'register' }));
			console.log('Registration mode activated');
		}
	}

	function clearDatabase() {
		if (confirm('Are you sure you want to clear the database?')) {
			ws.send(JSON.stringify({ action: 'clear' }));
		}
	}

	function sendSingleFrame() {
		if (!videoElement || !canvasContext) return;

		canvasContext.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
		const imageDataUrl = canvas.toDataURL('image/jpeg', 0.8);
		ws.send(imageDataUrl);
		frameCount++;
	}
</script>

<div class="container">
	<h1>Facial Recognition System</h1>

	<div class="status">
		<p>
			WebSocket Status: <span class={isConnected ? 'connected' : 'disconnected'}>
				{isConnected ? '✓ Connected' : '✗ Disconnected'}
			</span>
		</p>
		<p>Frames sent: {frameCount}</p>
	</div>

	<div class="video-container">
		<video bind:this={videoElement} />
		{#if faceDetected}
			<div class="face-detected">✓ Face Detected!</div>
		{/if}
	</div>

	<div class="controls">
		<button on:click={toggleRegister} class={registerMode ? 'active' : ''}>
			{registerMode ? 'Cancel Register' : 'Register Face'}
		</button>
		<button on:click={sendSingleFrame}>Send Frame</button>
		<button on:click={clearDatabase} class="danger">Clear Database</button>
	</div>

	{#if detectionResults}
		<div class="results">
			<h3>Detection Results</h3>
			<p>Faces detected: {detectionResults.face_count}</p>
			{#if detectionResults.faces && detectionResults.faces.length > 0}
				{#each detectionResults.faces as face, i}
					<div class="face-result">
						<p><strong>Face {i + 1}</strong></p>
						<p>Match: {face.matched_name || 'Unknown'}</p>
						<p>Similarity: {(face.similarity * 100).toFixed(2)}%</p>
						<p>Authorized: {face.authorized ? '✓ Yes' : '✗ No'}</p>
					</div>
				{/each}
			{/if}
		</div>
	{/if}
</div>

<style>
	.container {
		max-width: 800px;
		margin: 0 auto;
		padding: 20px;
		font-family: Arial, sans-serif;
	}

	h1 {
		text-align: center;
		color: #333;
	}

	.status {
		background: #f0f0f0;
		padding: 15px;
		border-radius: 5px;
		margin-bottom: 20px;
	}

	.status p {
		margin: 5px 0;
	}

	.connected {
		color: green;
		font-weight: bold;
	}

	.disconnected {
		color: red;
		font-weight: bold;
	}

	.video-container {
		position: relative;
		width: 100%;
		margin-bottom: 20px;
		background: #000;
		border-radius: 5px;
		overflow: hidden;
	}

	video {
		width: 100%;
		height: auto;
		display: block;
	}

	.face-detected {
		position: absolute;
		top: 10px;
		right: 10px;
		background: rgba(0, 255, 0, 0.8);
		color: white;
		padding: 10px 15px;
		border-radius: 5px;
		font-weight: bold;
	}

	.controls {
		display: flex;
		gap: 10px;
		margin-bottom: 20px;
	}

	button {
		flex: 1;
		padding: 12px;
		font-size: 16px;
		border: none;
		border-radius: 5px;
		cursor: pointer;
		background: #007bff;
		color: white;
		transition: background 0.3s;
	}

	button:hover {
		background: #0056b3;
	}

	button.active {
		background: #ff6b6b;
	}

	button.danger {
		background: #dc3545;
	}

	button.danger:hover {
		background: #c82333;
	}

	.results {
		background: #f9f9f9;
		padding: 15px;
		border-radius: 5px;
		border-left: 4px solid #007bff;
	}

	.results h3 {
		margin-top: 0;
	}

	.face-result {
		background: white;
		padding: 10px;
		margin: 10px 0;
		border-radius: 3px;
		border: 1px solid #ddd;
	}

	.face-result p {
		margin: 5px 0;
	}
</style>
