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

			// Handle clock-in/clock-out success
			if (data.type === 'clock_success') {
				faceDetected = true;
				detectionResults = {
					type: 'clock_verification',
					employee: data.employee,
					clock: data.clock,
					similarity: data.similarity,
					success: true
				};
				// Show clock confirmation to user
				const msg = `✓ ${data.clock.message}\n\nEmployee: ${data.employee.name}\nAction: ${data.clock.action.toUpperCase()}\nTime: ${new Date(data.clock.timestamp).toLocaleTimeString()}`;
				alert(msg);
				console.log(`Clock update: ${data.clock.message}`);
			}
			// Handle recognition failures
			else if (data.type === 'recognition_failed') {
				faceDetected = false;
				detectionResults = {
					type: 'recognition_failed',
					message: data.message,
					similarity: data.similarity,
					threshold: data.threshold,
					success: false
				};
				console.warn('Face not recognized:', data.message);
			}
			// Handle errors
			else if (data.type === 'error') {
				faceDetected = false;
				detectionResults = {
					type: 'error',
					message: data.message,
					success: false
				};
				console.warn('Error from server:', data.message);
			}
			// Handle command responses
			else if (data.type === 'command_response') {
				if (data.action === 'clear') {
					alert('✓ Database and clock status cleared');
				}
			}
			// Handle status updates
			else if (data.type === 'status_update') {
				console.log('Clock status update:', data.clock_status);
				detectionResults = {
					type: 'status',
					clock_status: data.clock_status
				};
			}
			// Handle employees list
			else if (data.type === 'employees_list') {
				console.log(`${data.count} employees registered:`, data.employees);
				detectionResults = {
					type: 'employees',
					employees: data.employees,
					count: data.count
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
		// Changed to display status instead (legacy)
		ws.send(JSON.stringify({ action: 'get_status' }));
	}

	function clearDatabase() {
		if (confirm('Are you sure you want to clear the database and clock data?')) {
			ws.send(JSON.stringify({ action: 'clear' }));
		}
	}

	function displayAllEmployees() {
		ws.send(JSON.stringify({ action: 'get_employees' }));
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
	<h1>Employee Clock-In System</h1>

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
		<button on:click={displayAllEmployees}>Show Employees</button>
		<button on:click={toggleRegister}>Show Status</button>
		<button on:click={sendSingleFrame}>Manual Verify</button>
		<button on:click={clearDatabase} class="danger">Clear System</button>
	</div>

	{#if detectionResults}
		<div class="results">
			{#if detectionResults.type === 'clock_verification'}
				<div class="clock-success">
					<h3>✓ Clock Verification Successful</h3>
					<div class="employee-info">
						<p><strong>Employee:</strong> {detectionResults.employee.name}</p>
						<p><strong>Action:</strong> {detectionResults.clock.action === 'clock_in' ? '🟢 CLOCKED IN' : '🔴 CLOCKED OUT'}</p>
						<p><strong>Time:</strong> {new Date(detectionResults.clock.timestamp).toLocaleString()}</p>
						<p><strong>Message:</strong> {detectionResults.clock.message}</p>
						<p><strong>Similarity:</strong> {(detectionResults.similarity * 100).toFixed(2)}%</p>
					</div>
				</div>
			{:else if detectionResults.type === 'recognition_failed'}
				<div class="recognition-failed">
					<h3>✗ Face Not Recognized</h3>
					<p>{detectionResults.message}</p>
					<p>Similarity: {(detectionResults.similarity * 100).toFixed(2)}% (threshold: {(detectionResults.threshold * 100).toFixed(2)}%)</p>
				</div>
			{:else if detectionResults.type === 'error'}
				<div class="error">
					<h3>Error</h3>
					<p>{detectionResults.message}</p>
				</div>
			{:else if detectionResults.type === 'status'}
				<div class="status-display">
					<h3>Clock Status</h3>
					{#if Object.keys(detectionResults.clock_status).length === 0}
						<p>No employees clocked in/out yet.</p>
					{:else}
						{#each Object.entries(detectionResults.clock_status) as [name, status]}
							<div class="status-item">
								<p><strong>{name}</strong></p>
								<p>Status: {status.clocked_in ? '🟢 CLOCKED IN' : '🔴 CLOCKED OUT'}</p>
								{#if status.clock_in_time}
									<p>Clock In: {new Date(status.clock_in_time).toLocaleString()}</p>
								{/if}
								{#if status.clock_out_time}
									<p>Clock Out: {new Date(status.clock_out_time).toLocaleString()}</p>
								{/if}
							</div>
						{/each}
					{/if}
				</div>
			{:else if detectionResults.type === 'employees'}
				<div class="employees-list">
					<h3>Registered Employees ({detectionResults.count})</h3>
					{#if detectionResults.count === 0}
						<p>No employees registered yet.</p>
					{:else}
						<ul>
							{#each detectionResults.employees as employee}
								<li>{employee}</li>
							{/each}
						</ul>
					{/if}
				</div>
			{/if}
		</div>
	{/if}
</div>

<style>
	.container {
		max-width: 900px;
		margin: 0 auto;
		padding: 20px;
		font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
		background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
		min-height: 100vh;
	}

	h1 {
		text-align: center;
		color: white;
		margin-bottom: 30px;
		font-size: 2em;
		text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
	}

	.status {
		background: rgba(255, 255, 255, 0.95);
		padding: 15px;
		border-radius: 8px;
		margin-bottom: 20px;
		box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
	}

	.status p {
		margin: 5px 0;
		color: #333;
	}

	.connected {
		color: #28a745;
		font-weight: bold;
		font-size: 1.1em;
	}

	.disconnected {
		color: #dc3545;
		font-weight: bold;
		font-size: 1.1em;
	}

	.video-container {
		position: relative;
		width: 100%;
		margin-bottom: 20px;
		background: #000;
		border-radius: 8px;
		overflow: hidden;
		box-shadow: 0 8px 16px rgba(0, 0, 0, 0.3);
		aspect-ratio: 4 / 3;
	}

	video {
		width: 100%;
		height: 100%;
		object-fit: cover;
		display: block;
	}

	.face-detected {
		position: absolute;
		top: 10px;
		right: 10px;
		background: rgba(40, 167, 69, 0.95);
		color: white;
		padding: 10px 15px;
		border-radius: 5px;
		font-weight: bold;
		animation: pulse 1.5s infinite;
	}

	@keyframes pulse {
		0%, 100% { opacity: 1; }
		50% { opacity: 0.7; }
	}

	.controls {
		display: flex;
		gap: 10px;
		margin-bottom: 20px;
		flex-wrap: wrap;
	}

	button {
		flex: 1;
		min-width: 150px;
		padding: 12px;
		font-size: 16px;
		border: none;
		border-radius: 8px;
		cursor: pointer;
		background: rgba(255, 255, 255, 0.95);
		color: #667eea;
		font-weight: bold;
		transition: all 0.3s ease;
		box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
	}

	button:hover {
		background: white;
		transform: translateY(-2px);
		box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
	}

	button.danger {
		background: #dc3545;
		color: white;
	}

	button.danger:hover {
		background: #c82333;
	}

	.results {
		background: rgba(255, 255, 255, 0.95);
		padding: 20px;
		border-radius: 8px;
		box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
		animation: slideIn 0.3s ease;
	}

	@keyframes slideIn {
		from {
			opacity: 0;
			transform: translateY(10px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	.clock-success {
		background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
		border-left: 6px solid #28a745;
		padding: 15px;
		border-radius: 5px;
	}

	.clock-success h3 {
		color: #155724;
		margin-top: 0;
		font-size: 1.3em;
	}

	.employee-info {
		background: white;
		padding: 15px;
		border-radius: 5px;
		margin-top: 10px;
	}

	.employee-info p {
		margin: 8px 0;
		color: #333;
	}

	.recognition-failed {
		background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
		border-left: 6px solid #dc3545;
		padding: 15px;
		border-radius: 5px;
	}

	.recognition-failed h3 {
		color: #721c24;
		margin-top: 0;
		font-size: 1.3em;
	}

	.recognition-failed p {
		color: #721c24;
	}

	.error {
		background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
		border-left: 6px solid #dc3545;
		padding: 15px;
		border-radius: 5px;
	}

	.error h3 {
		color: #721c24;
		margin-top: 0;
	}

	.error p {
		color: #721c24;
	}

	.status-display {
		background: #f9f9f9;
		padding: 15px;
		border-radius: 5px;
	}

	.status-display h3 {
		margin-top: 0;
		color: #333;
	}

	.status-item {
		background: white;
		padding: 10px;
		margin: 10px 0;
		border-radius: 5px;
		border: 2px solid #667eea;
	}

	.status-item p {
		margin: 5px 0;
		color: #333;
	}

	.employees-list {
		background: #f9f9f9;
		padding: 15px;
		border-radius: 5px;
	}

	.employees-list h3 {
		margin-top: 0;
		color: #333;
	}

	.employees-list ul {
		list-style: none;
		padding: 0;
		margin: 0;
	}

	.employees-list li {
		background: white;
		padding: 10px;
		margin: 8px 0;
		border-radius: 5px;
		border-left: 4px solid #667eea;
		color: #333;
	}
</style>
