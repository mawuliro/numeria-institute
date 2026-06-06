class NumeriaConference {
    constructor() {
        this.lobbyContainer = document.querySelector('#lobby-container');
        this.meetingContainer = document.querySelector('#meeting-app');
        this.localStream = null;
        this.screenStream = null;
        this.pcByPeer = {};
        this.pendingRequests = {};
        this.remoteParticipants = {};
        this.ws = null;
        this.peerId = this.generatePeerId();
        this.connected = false;
        this.reconnectAttempts = 0;
        this.isHost = false;
        this.roomCode = '';
        this.displayName = '';
        this.roomTitle = '';
        this.maxParticipants = 6;
        this.timerInterval = null;
        this.startTimestamp = Date.now();
    }

    init() {
        if (this.lobbyContainer) {
            this.initLobby();
        }
        if (this.meetingContainer) {
            this.initMeeting();
        }
    }

    initLobby() {
        this.roomCode = this.getMeta('room-code');
        this.displayName = this.getMeta('display-name') || localStorage.getItem('numeria_visio_name') || '';

        const previewVideo = document.querySelector('#previewVideo');
        const cameraSelect = document.querySelector('#cameraSelect');
        const microphoneSelect = document.querySelector('#microphoneSelect');
        const displayNameInput = document.querySelector('#displayName');
        const joinButton = document.querySelector('#joinButton');
        const blurCheckbox = document.querySelector('#blurBackground');
        const errorContainer = document.querySelector('#lobbyError');

        displayNameInput.value = this.displayName;
        displayNameInput.addEventListener('input', () => {
            if (errorContainer) {
                errorContainer.classList.add('hidden');
            }
        });

        joinButton.addEventListener('click', async () => {
            try {
                const name = displayNameInput.value.trim();
                if (!name) {
                    this.showLobbyError('Veuillez entrer un nom affiché.');
                    return;
                }

                const cameraId = cameraSelect.value;
                const microphoneId = microphoneSelect.value;
                const blur = blurCheckbox.checked;

                localStorage.setItem('numeria_visio_name', name);
                localStorage.setItem('numeria_visio_camera', cameraId);
                localStorage.setItem('numeria_visio_microphone', microphoneId);
                localStorage.setItem('numeria_visio_blur', blur ? '1' : '0');

                const url = new URL(window.location.href);
                url.searchParams.set('joined', '1');
                url.searchParams.set('display_name', name);
                window.location.href = url.toString();
            } catch (error) {
                this.showLobbyError('Impossible de rejoindre la réunion. Vérifiez vos autorisations.');
                console.error(error);
            }
        });

        this.attachLobbyListeners();
        this.refreshDevices();
        this.updatePreview();
    }

    showLobbyError(message) {
        const errorContainer = document.querySelector('#lobbyError');
        if (!errorContainer) return;
        errorContainer.textContent = message;
        errorContainer.classList.remove('hidden');
    }

    attachLobbyListeners() {
        const cameraSelect = document.querySelector('#cameraSelect');
        const microphoneSelect = document.querySelector('#microphoneSelect');

        cameraSelect?.addEventListener('change', () => this.updatePreview());
        microphoneSelect?.addEventListener('change', () => this.updatePreview());

        navigator.mediaDevices.addEventListener('devicechange', () => this.refreshDevices());
    }

    async refreshDevices() {
        try {
            const devices = await navigator.mediaDevices.enumerateDevices();
            const cameras = devices.filter(device => device.kind === 'videoinput');
            const microphones = devices.filter(device => device.kind === 'audioinput');
            this.populateDeviceSelect('#cameraSelect', cameras, 'Caméra');
            this.populateDeviceSelect('#microphoneSelect', microphones, 'Microphone');
            await this.updatePreview();
        } catch (error) {
            console.warn('Impossible de lister les appareils.', error);
        }
    }

    populateDeviceSelect(selector, devices, label) {
        const element = document.querySelector(selector);
        if (!element) {
            return;
        }

        const selectedId = localStorage.getItem(selector === '#cameraSelect' ? 'numeria_visio_camera' : 'numeria_visio_microphone');
        element.innerHTML = '';

        devices.forEach((device, index) => {
            const option = document.createElement('option');
            option.value = device.deviceId;
            option.textContent = device.label || `${label} ${index + 1}`;
            element.appendChild(option);
        });

        if (selectedId && devices.some(device => device.deviceId === selectedId)) {
            element.value = selectedId;
        }
    }

    async updatePreview() {
        const previewVideo = document.querySelector('#previewVideo');
        const cameraSelect = document.querySelector('#cameraSelect');
        const microphoneSelect = document.querySelector('#microphoneSelect');
        if (!previewVideo || !cameraSelect || !microphoneSelect) return;

        const cameraId = cameraSelect.value || undefined;
        const microphoneId = microphoneSelect.value || undefined;

        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: cameraId ? {deviceId: {exact: cameraId}} : true,
                audio: microphoneId ? {deviceId: {exact: microphoneId}} : false,
            });
            previewVideo.srcObject = stream;
        } catch (error) {
            this.showLobbyError('Impossible d’accéder à la caméra ou au micro. Autorisez l’accès et rechargez la page.');
            console.error(error);
        }
    }

    async initMeeting() {
        this.roomCode = this.meetingContainer.dataset.roomCode;
        this.displayName = this.meetingContainer.dataset.displayName || localStorage.getItem('numeria_visio_name') || 'Participant';
        this.isHost = this.meetingContainer.dataset.isHost === 'true';
        this.roomTitle = this.meetingContainer.dataset.roomTitle || 'Réunion';
        this.maxParticipants = Number(this.meetingContainer.dataset.maxParticipants) || 6;

        this.chatInput = document.querySelector('#chatInput');
        this.chatSend = document.querySelector('#chatSend');
        this.videoGrid = document.querySelector('#video-grid');
        this.unreadBadge = document.querySelector('#unreadBadge');
        this.sidebar = document.querySelector('#sidebar');
        this.waitingOverlay = document.querySelector('#waitingOverlay');
        this.notificationToast = document.querySelector('#notificationToast');
        this.participantsList = document.querySelector('#participantsList');

        this.bindMeetingEvents();
        await this.prepareLocalMedia();
        this.connectSocket();
        this.startTimer();
    }

    bindMeetingEvents() {
        document.querySelector('#toggleMute')?.addEventListener('click', () => this.toggleMute());
        document.querySelector('#toggleCamera')?.addEventListener('click', () => this.toggleCamera());
        document.querySelector('#screenShare')?.addEventListener('click', () => this.toggleScreenShare());
        document.querySelector('#raiseHand')?.addEventListener('click', () => this.toggleRaiseHand());
        document.querySelector('#toggleChat')?.addEventListener('click', () => this.togglePanel('chat'));
        document.querySelector('#toggleParticipants')?.addEventListener('click', () => this.togglePanel('participants'));
        document.querySelector('#chatSend')?.addEventListener('click', () => this.sendChat());
        document.querySelector('#chatInput')?.addEventListener('keydown', event => { if (event.key === 'Enter') { event.preventDefault(); this.sendChat(); }});
        document.querySelector('#copyRoomCode')?.addEventListener('click', () => this.copyRoomCode());
        document.querySelector('#leaveButton')?.addEventListener('click', () => this.leaveMeeting());
        document.querySelector('#closeSidebar')?.addEventListener('click', () => this.sidebar?.classList.add('hidden'));
        document.querySelectorAll('#sidebarTabs button').forEach(button => {
            button.addEventListener('click', () => {
                this.togglePanel(button.dataset.panel);
            });
        });
    }

    async prepareLocalMedia() {
        try {
            const cameraId = localStorage.getItem('numeria_visio_camera');
            const microphoneId = localStorage.getItem('numeria_visio_microphone');
            const constraints = {
                video: cameraId ? {deviceId: {exact: cameraId}} : {width: {ideal: 1280}, height: {ideal: 720}},
                audio: microphoneId ? {deviceId: {exact: microphoneId}} : true,
            };
            this.localStream = await navigator.mediaDevices.getUserMedia(constraints);
            this.audioTrack = this.localStream.getAudioTracks()[0] || null;
            this.videoTrack = this.localStream.getVideoTracks()[0] || null;
            this.attachLocalTile();
        } catch (error) {
            this.showNotification('Impossible d’accéder au micro ou à la caméra. Vérifiez les autorisations du navigateur.', true);
            console.error(error);
        }
    }

    attachLocalTile() {
        const existing = document.querySelector('#tile-self');
        if (existing) {
            const video = existing.querySelector('video');
            if (video && this.localStream) video.srcObject = this.localStream;
            return;
        }

        const tile = document.createElement('div');
        tile.id = 'tile-self';
        tile.className = 'relative overflow-hidden rounded-3xl bg-[#111117] shadow-inner shadow-black/40';
        tile.innerHTML = `
            <video autoplay muted playsinline class="h-full w-full object-cover"></video>
            <div class="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent"></div>
            <div class="absolute left-4 bottom-4 flex flex-wrap items-center gap-2 text-sm text-white">
                <span class="rounded-full bg-[#2D8CFF] px-3 py-1">Vous</span>
                <span class="rounded-full bg-white/10 px-3 py-1">${this.displayName}</span>
            </div>
        `;
        const video = tile.querySelector('video');
        if (video) video.srcObject = this.localStream;
        this.videoGrid.prepend(tile);
    }

    async connectSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
        const wsUrl = `${protocol}://${window.location.host}/ws/visio/${this.roomCode}/`;

        this.ws = new WebSocket(wsUrl);
        this.ws.onopen = () => {
            this.connected = true;
            this.reconnectAttempts = 0;
            this.sendSignal('join_room', {peer_id: this.peerId, display_name: this.displayName});
        };
        this.ws.onmessage = event => this.handleSocketMessage(event);
        this.ws.onclose = () => {
            this.connected = false;
            this.showNotification('Connexion WebSocket interrompue. Reconnexion en cours…');
            this.reconnectWebSocket();
        };
        this.ws.onerror = () => {
            this.showNotification('Erreur de signalisation. Vérifiez votre connexion.', true);
        };
    }

    reconnectWebSocket() {
        if (this.reconnectAttempts > 5) {
            this.showNotification('Impossible de se reconnecter. Rechargez la page.', true);
            return;
        }

        this.reconnectAttempts += 1;
        const delay = Math.min(30000, 1000 * Math.pow(2, this.reconnectAttempts));
        setTimeout(() => this.connectSocket(), delay);
    }

    handleSocketMessage(event) {
        const payload = JSON.parse(event.data);
        switch (payload.type) {
            case 'room_state':
                this.isHost = payload.is_host;
                this.renderParticipantList(payload.participants);
                break;
            case 'waiting_for_admission':
                this.setWaitingOverlay(true);
                break;
            case 'waiting_room_request':
                if (this.isHost) {
                    this.addPendingRequest(payload);
                }
                break;
            case 'participant_approved':
                if (payload.peer_id === this.peerId) {
                    this.setWaitingOverlay(false);
                    this.showNotification('Vous avez été admis dans la réunion.');
                }
                break;
            case 'participant_join':
                this.handleParticipantJoin(payload);
                break;
            case 'host_arrived':
                if (payload.peer_id !== this.peerId) {
                    this.createOfferToNewPeer(payload.peer_id, payload.display_name);
                }
                break;
            case 'participant_leave':
                this.removeParticipant(payload.peer_id);
                break;
            case 'offer':
                if (payload.target === this.peerId) {
                    this.handleOffer(payload);
                }
                break;
            case 'answer':
                if (payload.target === this.peerId) {
                    this.handleAnswer(payload);
                }
                break;
            case 'ice_candidate':
                if (payload.target === this.peerId) {
                    this.handleIceCandidate(payload);
                }
                break;
            case 'chat_message':
                this.appendChatMessage(payload.sender, payload.content, payload.timestamp);
                break;
            case 'raise_hand':
            case 'mute_status':
            case 'camera_status':
                this.updateRemoteStatus(payload);
                break;
            case 'meeting_ended':
                this.showNotification('La réunion est terminée par l’hôte.', true);
                this.setWaitingOverlay(true, 'La réunion a pris fin.');
                break;
            case 'error':
                this.showNotification(payload.message, true);
                break;
            default:
                console.warn('Événement WebSocket inconnu', payload);
        }
    }

    setWaitingOverlay(show, message = null) {
        if (!this.waitingOverlay) return;
        this.waitingOverlay.querySelector('h2').textContent = message || 'En attente d’admission';
        this.waitingOverlay.querySelector('p').textContent = message ? message : 'Un·e hôte examine votre demande. Vous serez admis·e dès que possible.';
        this.waitingOverlay.classList.toggle('hidden', !show);
    }

    addPendingRequest(payload) {
        if (!payload.peer_id) return;
        this.pendingRequests[payload.peer_id] = payload.display_name;
        this.showNotification(`Nouvelle demande d’admission : ${payload.display_name}`);
        this.renderParticipantList(Object.values(this.remoteParticipants));
    }

    renderParticipantList(participants) {
        if (!this.participantsList) return;
        this.participantsList.innerHTML = '';
        if (!Array.isArray(participants)) {
            participants = [];
        }

        for (const participant of participants) {
            const item = document.createElement('div');
            item.className = 'rounded-3xl border border-white/10 bg-[#111117] p-4 text-sm';
            item.innerHTML = `
                <div class="flex items-center justify-between gap-3">
                    <div>
                        <div class="font-semibold text-white">${participant.display_name}</div>
                        <div class="mt-1 text-xs text-slate-400">${participant.is_host ? 'Hôte' : 'Participant'}</div>
                    </div>
                    <div class="flex items-center gap-2 text-xs text-slate-300">
                        ${participant.is_muted ? '<span class="rounded-full bg-red-600 px-2 py-1">Muet</span>' : ''}
                        ${participant.camera_on ? '<span class="rounded-full bg-emerald-600 px-2 py-1">Caméra</span>' : '<span class="rounded-full bg-slate-600 px-2 py-1">Caméra coupée</span>'}
                    </div>
                </div>
            `;
            this.participantsList.appendChild(item);
        }

        if (this.isHost && Object.keys(this.pendingRequests).length > 0) {
            const requested = document.createElement('div');
            requested.className = 'mt-5 rounded-3xl border border-yellow-500/20 bg-[#16161A] p-4';
            requested.innerHTML = '<div class="mb-3 text-sm font-semibold text-yellow-300">Demandes en attente</div>';
            Object.entries(this.pendingRequests).forEach(([peerId, name]) => {
                const requestRow = document.createElement('div');
                requestRow.className = 'mb-3 flex items-center justify-between gap-3 rounded-2xl bg-[#111117] p-3';
                requestRow.innerHTML = `
                    <div>
                        <div class="font-medium text-white">${name}</div>
                        <div class="text-xs text-slate-400">En attente d’admission</div>
                    </div>
                    <button class="admit-button rounded-full bg-[#2D8CFF] px-4 py-2 text-xs font-semibold text-white">Admettre</button>
                `;
                requestRow.querySelector('.admit-button').addEventListener('click', () => this.admitParticipant(peerId));
                requested.appendChild(requestRow);
            });
            this.participantsList.appendChild(requested);
        }
    }

    async admitParticipant(peerId) {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
        this.sendSignal('admit_participant', {peer_id: peerId});
        delete this.pendingRequests[peerId];
        this.renderParticipantList(Object.values(this.remoteParticipants));
    }

    async createOfferToNewPeer(peerId, displayName) {
        if (peerId === this.peerId || this.pcByPeer[peerId]) return;
        const pc = this.createPeerConnection(peerId, displayName);
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);
        this.sendSignal('offer', {target: peerId, sdp: pc.localDescription});
    }

    handleParticipantJoin(payload) {
        if (!payload.peer_id || payload.peer_id === this.peerId) {
            return;
        }
        this.remoteParticipants[payload.peer_id] = {
            peer_id: payload.peer_id,
            display_name: payload.display_name,
            is_host: false,
            is_muted: false,
            camera_on: true,
        };
        this.createOfferToNewPeer(payload.peer_id, payload.display_name);
        this.renderParticipantList(Object.values(this.remoteParticipants));
        this.showNotification(`${payload.display_name} a rejoint la réunion.`);
    }

    async handleOffer(payload) {
        if (!payload.sender || payload.target !== this.peerId) {
            return;
        }
        const pc = this.createPeerConnection(payload.sender, payload.sender_display_name);
        const desc = new RTCSessionDescription(payload.sdp);
        await pc.setRemoteDescription(desc);
        const answer = await pc.createAnswer();
        await pc.setLocalDescription(answer);
        this.sendSignal('answer', {target: payload.sender, sdp: pc.localDescription});
    }

    async handleAnswer(payload) {
        if (!payload.sender || payload.target !== this.peerId || !this.pcByPeer[payload.sender]) {
            return;
        }
        const pc = this.pcByPeer[payload.sender];
        const desc = new RTCSessionDescription(payload.sdp);
        await pc.setRemoteDescription(desc);
    }

    async handleIceCandidate(payload) {
        if (!payload.sender || payload.target !== this.peerId || !this.pcByPeer[payload.sender] || !payload.candidate) {
            return;
        }
        try {
            await this.pcByPeer[payload.sender].addIceCandidate(new RTCIceCandidate(payload.candidate));
        } catch (error) {
            console.warn('Échec ajout ICE candidate:', error);
        }
    }

    createPeerConnection(peerId, displayName = 'Participant') {
        if (this.pcByPeer[peerId]) {
            return this.pcByPeer[peerId];
        }
        const pc = new RTCPeerConnection({
            iceServers: [
                {urls: ['stun:stun.l.google.com:19302']},
                {urls: ['stun:stun1.l.google.com:19302']},
            ],
        });

        pc.onicecandidate = event => {
            if (event.candidate) {
                this.sendSignal('ice_candidate', {target: peerId, candidate: event.candidate});
            }
        };

        pc.ontrack = event => {
            this.attachRemoteTile(peerId, displayName, event.streams[0]);
        };

        pc.onconnectionstatechange = () => {
            this.updateTileQuality(peerId, pc.connectionState);
            if (pc.connectionState === 'failed' || pc.connectionState === 'disconnected') {
                this.removeParticipant(peerId);
            }
        };

        if (this.localStream) {
            for (const track of this.localStream.getTracks()) {
                pc.addTrack(track, this.localStream);
            }
        }

        this.pcByPeer[peerId] = pc;
        return pc;
    }

    attachRemoteTile(peerId, displayName, stream) {
        const existingTile = document.getElementById(`tile-${peerId}`);
        if (existingTile) {
            const video = existingTile.querySelector('video');
            if (video) video.srcObject = stream;
            return;
        }

        const tile = document.createElement('div');
        tile.id = `tile-${peerId}`;
        tile.className = 'relative overflow-hidden rounded-3xl bg-[#111117] shadow-inner shadow-black/40';
        tile.innerHTML = `
            <video autoplay playsinline class="h-full w-full object-cover"></video>
            <div class="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent"></div>
            <div class="absolute left-4 bottom-4 flex flex-col gap-2 text-sm text-white">
                <span class="rounded-full bg-[#2D8CFF] px-3 py-1">${displayName}</span>
                <div id="status-${peerId}" class="flex gap-2 text-xs text-slate-200"></div>
            </div>
        `;
        const video = tile.querySelector('video');
        if (video) video.srcObject = stream;
        this.videoGrid.appendChild(tile);
        this.updateLayout();
    }

    removeParticipant(peerId) {
        const tile = document.getElementById(`tile-${peerId}`);
        if (tile) tile.remove();
        if (this.pcByPeer[peerId]) {
            this.pcByPeer[peerId].close();
            delete this.pcByPeer[peerId];
        }
        this.renderParticipantList([]);
        this.updateLayout();
    }

    updateTileQuality(peerId, state) {
        const status = document.getElementById(`status-${peerId}`);
        if (!status) return;
        const stateLabel = state === 'connected' ? 'Bon' : state === 'connecting' ? 'Connexion...' : 'Faible';
        status.textContent = `Qualité : ${stateLabel}`;
    }

    toggleMute() {
        if (!this.audioTrack) return;
        this.audioTrack.enabled = !this.audioTrack.enabled;
        this.sendSignal('mute_status', {value: this.audioTrack.enabled});
        this.showNotification(this.audioTrack.enabled ? 'Micro activé' : 'Micro coupé');
    }

    toggleCamera() {
        if (!this.videoTrack) return;
        this.videoTrack.enabled = !this.videoTrack.enabled;
        this.sendSignal('camera_status', {value: this.videoTrack.enabled});
        this.showNotification(this.videoTrack.enabled ? 'Caméra activée' : 'Caméra désactivée');
    }

    async toggleScreenShare() {
        if (this.screenStream) {
            this.stopScreenShare();
            return;
        }

        try {
            this.screenStream = await navigator.mediaDevices.getDisplayMedia({video: true});
            const screenTrack = this.screenStream.getVideoTracks()[0];
            for (const peerId of Object.keys(this.pcByPeer)) {
                const sender = this.pcByPeer[peerId].getSenders().find(s => s.track && s.track.kind === 'video');
                if (sender) {
                    sender.replaceTrack(screenTrack);
                }
            }
            const selfVideo = document.querySelector('#tile-self video');
            if (selfVideo) {
                const updatedStream = new MediaStream([screenTrack, ...(this.localStream.getAudioTracks() || [])]);
                selfVideo.srcObject = updatedStream;
            }
            screenTrack.onended = () => this.stopScreenShare();
            this.showNotification('Partage d’écran activé');
        } catch (error) {
            this.showNotification('Impossible de partager l’écran.', true);
            console.error(error);
        }
    }

    stopScreenShare() {
        if (!this.screenStream) return;
        this.screenStream.getTracks().forEach(track => track.stop());
        this.screenStream = null;
        for (const peerId of Object.keys(this.pcByPeer)) {
            const sender = this.pcByPeer[peerId].getSenders().find(s => s.track && s.track.kind === 'video');
            if (sender && this.videoTrack) {
                sender.replaceTrack(this.videoTrack);
            }
        }
        const selfVideo = document.querySelector('#tile-self video');
        if (selfVideo && this.localStream) {
            selfVideo.srcObject = this.localStream;
        }
        this.showNotification('Partage d’écran arrêté');
    }

    toggleRaiseHand() {
        this.sendSignal('raise_hand', {value: true});
        this.showNotification('Main levée');
    }

    togglePanel(panel) {
        this.sidebar?.classList.remove('hidden');
        document.querySelector('#panelChat')?.classList.toggle('hidden', panel !== 'chat');
        document.querySelector('#panelParticipants')?.classList.toggle('hidden', panel !== 'participants');
    }

    sendChat() {
        if (!this.chatInput || !this.chatInput.value.trim()) return;
        this.sendSignal('chat_message', {message: this.chatInput.value.trim()});
        this.chatInput.value = '';
    }

    appendChatMessage(sender, content, timestamp) {
        if (!this.chatMessages) {
            this.chatMessages = document.querySelector('#chatMessages');
        }
        if (!this.chatMessages) return;
        const item = document.createElement('div');
        item.className = 'rounded-2xl bg-[#111117] p-3 text-sm text-slate-300';
        item.innerHTML = `<span class="font-semibold text-white">${sender}</span> : ${content}`;
        this.chatMessages.appendChild(item);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        if (document.querySelector('#panelChat')?.classList.contains('hidden')) {
            this.unreadBadge?.classList.remove('hidden');
        }
    }

    updateRemoteStatus(payload) {
        const videoTile = document.getElementById(`tile-${payload.peer_id}`);
        if (!videoTile) return;
        const statusElement = videoTile.querySelector(`#status-${payload.peer_id}`);
        if (!statusElement) return;
        const statusText = payload.type === 'mute_status'
            ? (payload.value ? 'Micro activé' : 'Micro coupé')
            : payload.type === 'camera_status'
                ? (payload.value ? 'Caméra activée' : 'Caméra désactivée')
                : payload.type === 'raise_hand'
                    ? 'Main levée'
                    : '';
        statusElement.textContent = statusText;
    }

    copyRoomCode() {
        navigator.clipboard.writeText(this.roomCode).then(() => {
            this.showNotification('Code de réunion copié dans le presse-papiers.');
        });
    }

    leaveMeeting() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.sendSignal('leave_room', {peer_id: this.peerId});
        }
        window.location.href = '/';
    }

    sendSignal(type, payload = {}) {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            return;
        }
        this.ws.send(JSON.stringify({type, ...payload}));
    }

    showNotification(message, isError = false) {
        if (!this.notificationToast) return;
        this.notificationToast.textContent = message;
        this.notificationToast.classList.remove('hidden');
        this.notificationToast.classList.toggle('bg-red-700', isError);
        this.notificationToast.classList.toggle('bg-[#111117]', !isError);
        setTimeout(() => this.notificationToast?.classList.add('hidden'), 4500);
    }

    updateLayout() {
        const tiles = [...this.videoGrid.children];
        const count = tiles.length;
        let columns = 1;
        if (count === 2) columns = 2;
        else if (count === 3 || count === 4) columns = 2;
        else if (count >= 5) columns = 3;
        let classes = 'grid h-full gap-4';
        if (columns === 1) {
            classes += ' grid-cols-1';
        } else if (columns === 2) {
            classes += ' grid-cols-1 sm:grid-cols-2';
        } else {
            classes += ' grid-cols-1 sm:grid-cols-2 lg:grid-cols-3';
        }
        this.videoGrid.className = classes;
    }

    startTimer() {
        const timerElement = document.querySelector('#meetingTimer');
        if (!timerElement) return;
        this.timerInterval = setInterval(() => {
            const elapsed = Math.floor((Date.now() - this.startTimestamp) / 1000);
            timerElement.textContent = this.formatDuration(elapsed);
        }, 1000);
    }

    formatDuration(seconds) {
        const h = String(Math.floor(seconds / 3600)).padStart(2, '0');
        const m = String(Math.floor((seconds % 3600) / 60)).padStart(2, '0');
        const s = String(seconds % 60).padStart(2, '0');
        return `${h}:${m}:${s}`;
    }

    getMeta(key) {
        return this.lobbyContainer?.dataset[key] || this.meetingContainer?.dataset[key] || '';
    }

    generatePeerId() {
        return `peer_${Math.random().toString(16).slice(2)}_${Date.now()}`;
    }
}

window.addEventListener('DOMContentLoaded', () => new NumeriaConference().init());
