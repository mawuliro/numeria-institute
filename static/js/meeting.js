/* eslint-disable no-console */
console.log('✅ meeting.js loaded');

class NumeriaConference {
    constructor() {
        this.roomCode = typeof ROOM_CODE !== 'undefined' ? ROOM_CODE : null;
        this.displayName = document.querySelector('#meeting-app')?.dataset.displayName || 'Participant';
        this.isHost = document.querySelector('#meeting-app')?.dataset.isHost === 'true';
        this.roomTitle = document.querySelector('#meeting-app')?.dataset.roomTitle || '';
        this.websocket = null;
        this.localStream = null;
        this.peerConnections = new Map();
        this.signalingUrl = null;
        this.currentUser = typeof CURRENT_USER !== 'undefined' ? CURRENT_USER : this.displayName;

        this.statusElement = null;
        this.participantCountElement = null;
        this.errorElement = null;
        this.localVideoElement = null;
        this.copyButton = null;
    }

    init() {
        if (!this.roomCode) {
            console.error('Room code is missing, meeting cannot start.');
            return;
        }

        this.statusElement = document.querySelector('#connectionStatus');
        this.participantCountElement = document.querySelector('#participantCount');
        this.errorElement = document.querySelector('#meetingError');
        this.localVideoElement = document.querySelector('#local-video');
        this.copyButton = document.querySelector('#copyRoomCode');

        if (!this.statusElement || !this.localVideoElement) {
            console.error('Meeting elements are missing from the page.');
            return;
        }

        this.setupButtons();
        this.updateConnectionStatus('Initialisation du meeting...', false);
        this.prepareLocalMedia()
            .finally(() => {
                this.connectWebSocket();
            });
    }

    setupButtons() {
        this.copyButton?.addEventListener('click', () => {
            navigator.clipboard.writeText(this.roomCode)
                .then(() => this.showToast('Code de réunion copié'))
                .catch(() => this.showToast('Impossible de copier le code', true));
        });

        document.querySelector('#leaveButton')?.addEventListener('click', () => {
            window.location.href = '/';
        });
    }

    async prepareLocalMedia() {
        try {
            this.localStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: true });
            this.localVideoElement.srcObject = this.localStream;
            this.localVideoElement.onloadedmetadata = () => this.localVideoElement.play().catch(() => {});
            this.updateConnectionStatus('Caméra et micro prêts. Connexion au signal...', false);
        } catch (err) {
            console.warn('getUserMedia failed:', err);
            this.localVideoElement.classList.add('bg-black');
            this.showError('Impossible d’accéder à la caméra ou au micro. Vérifiez les permissions du navigateur.');
            this.updateConnectionStatus('Connexion au signal sans média local', true);
        }
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
        this.signalingUrl = `${protocol}://${window.location.host}/ws/visioconference/${this.roomCode}/`;

        this.updateConnectionStatus('Connexion WebSocket en cours...', false);
        console.log('Connecting to WebSocket:', this.signalingUrl);

        this.websocket = new WebSocket(this.signalingUrl);
        this.websocket.addEventListener('open', () => this.handleSocketOpen());
        this.websocket.addEventListener('message', (event) => this.handleSocketMessage(event));
        this.websocket.addEventListener('close', (event) => this.handleSocketClose(event));
        this.websocket.addEventListener('error', (event) => this.handleSocketError(event));
    }

    handleSocketOpen() {
        console.log('WebSocket ouvert. Envoi de la requête de jointure.');
        this.updateConnectionStatus('WebSocket connecté. Envoi de la requête de réunion...', false);
        this.sendSignal('join_room', {
            display_name: this.displayName,
            peer_id: this.generatePeerId(),
            room_code: this.roomCode,
        });
    }

    handleSocketMessage(event) {
        let payload;
        try {
            payload = JSON.parse(event.data);
        } catch (err) {
            console.error('Impossible de parser le message WebSocket:', err, event.data);
            return;
        }

        console.log('WebSocket message reçu:', payload);
        const type = payload.type;

        if (type === 'offer') {
            this.handleOffer(payload);
            return;
        }

        if (type === 'answer') {
            this.handleAnswer(payload);
            return;
        }

        if (type === 'ice') {
            this.handleIce(payload);
            return;
        }

        if (type === 'participant_join' || type === 'user_joined') {
            this.handleNewParticipant(payload);
            return;
        }

        if (type === 'host_arrived') {
            this.showToast('L’hôte est arrivé dans la salle.');
            return;
        }

        if (type === 'waiting_for_admission') {
            this.updateConnectionStatus('En attente d’admission...', false);
            return;
        }

        if (type === 'admitted') {
            this.updateConnectionStatus('Admis dans la réunion. Création d’un appel...', false);
            return;
        }

        if (type === 'error') {
            this.showError(payload.message || 'Erreur de signalisation.');
            return;
        }

        if (type === 'participant_count') {
            this.updateParticipantCount(payload.count);
            return;
        }
    }

    handleSocketClose(event) {
        console.warn('WebSocket fermé:', event);
        this.updateConnectionStatus('WebSocket déconnecté. Actualisez la page si nécessaire.', true);
        this.showToast('Connexion perdue. Reconnectez-vous.', true);
    }

    handleSocketError(event) {
        console.error('WebSocket error:', event);
        this.updateConnectionStatus('Erreur WebSocket détectée.', true);
        this.showToast('Erreur de connexion en temps réel.', true);
    }

    sendSignal(type, payload = {}) {
        if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
            console.warn('WebSocket non prêt pour envoyer le signal:', type);
            return;
        }

        const message = JSON.stringify({ type, ...payload });
        this.websocket.send(message);
        console.log('Signal envoyé:', message);
    }

    async handleNewParticipant(payload) {
        this.updateParticipantCount((payload.count || 0) + 1);
        this.showToast(`${payload.display_name || 'Un participant'} a rejoint la réunion.`);
        await this.createOfferToPeer(payload.peer_id);
    }

    async createOfferToPeer(peerId) {
        if (!peerId || this.peerConnections.has(peerId)) {
            return;
        }

        const peerConnection = this.createPeerConnection(peerId);
        this.peerConnections.set(peerId, peerConnection);

        try {
            const offer = await peerConnection.createOffer();
            await peerConnection.setLocalDescription(offer);
            this.sendSignal('offer', {
                target: peerId,
                sdp: offer.sdp,
                display_name: this.displayName,
                peer_id: peerId,
            });
        } catch (err) {
            console.error('Erreur lors de la création de l’offre:', err);
            this.showError('Échec de création de l’offre WebRTC.');
        }
    }

    async handleOffer(payload) {
        const { peer_id: peerId, sdp } = payload;
        if (!peerId || !sdp) {
            return;
        }

        const peerConnection = this.peerConnections.get(peerId) || this.createPeerConnection(peerId);
        this.peerConnections.set(peerId, peerConnection);

        try {
            await peerConnection.setRemoteDescription({ type: 'offer', sdp });
            const answer = await peerConnection.createAnswer();
            await peerConnection.setLocalDescription(answer);
            this.sendSignal('answer', {
                target: peerId,
                sdp: answer.sdp,
                display_name: this.displayName,
                peer_id: peerId,
            });
        } catch (err) {
            console.error('Erreur lors du traitement de l’offre:', err);
            this.showError('Impossible de traiter l’offre WebRTC.');
        }
    }

    async handleAnswer(payload) {
        const { peer_id: peerId, sdp } = payload;
        const peerConnection = this.peerConnections.get(peerId);
        if (!peerConnection || !sdp) {
            return;
        }

        try {
            await peerConnection.setRemoteDescription({ type: 'answer', sdp });
        } catch (err) {
            console.error('Erreur lors du traitement de la réponse:', err);
            this.showError('Impossible de traiter la réponse WebRTC.');
        }
    }

    async handleIce(payload) {
        const { peer_id: peerId, candidate } = payload;
        const peerConnection = this.peerConnections.get(peerId);
        if (!peerConnection || !candidate) {
            return;
        }

        try {
            await peerConnection.addIceCandidate(candidate);
        } catch (err) {
            console.error('Erreur ajout ICE candidate:', err);
        }
    }

    createPeerConnection(peerId) {
        const peerConnection = new RTCPeerConnection({
            iceServers: [
                { urls: ['stun:stun.l.google.com:19302'] },
            ],
        });

        peerConnection.onicecandidate = ({ candidate }) => {
            if (!candidate) {
                return;
            }
            this.sendSignal('ice', {
                target: peerId,
                candidate,
                peer_id: peerId,
            });
        };

        peerConnection.ontrack = ({ streams }) => {
            const stream = streams[0];
            if (!stream) {
                return;
            }
            this.attachRemoteStream(peerId, stream);
        };

        peerConnection.onconnectionstatechange = () => {
            console.log(`Peer ${peerId} state:`, peerConnection.connectionState);
            if (peerConnection.connectionState === 'failed') {
                this.showToast(`Connexion au pair ${peerId} échouée.`, true);
            }
        };

        if (this.localStream) {
            for (const track of this.localStream.getTracks()) {
                peerConnection.addTrack(track, this.localStream);
            }
        }

        return peerConnection;
    }

    attachRemoteStream(peerId, stream) {
        let remoteVideo = document.querySelector(`#remote-video-${peerId}`);
        if (!remoteVideo) {
            const videoGrid = document.querySelector('#video-grid');
            const card = document.createElement('div');
            card.className = 'relative overflow-hidden rounded-3xl bg-[#111117] shadow-inner shadow-black/40';
            card.innerHTML = `
                <div class="absolute inset-0 bg-[#000000] opacity-30"></div>
                <video id="remote-video-${peerId}" autoplay playsinline class="h-full w-full object-cover"></video>
                <div class="absolute left-4 bottom-4 rounded-full bg-[#38BDF8] px-3 py-1 text-sm text-white">Participant</div>
            `;
            videoGrid.appendChild(card);
            remoteVideo = card.querySelector('video');
        }
        remoteVideo.srcObject = stream;
        remoteVideo.onloadedmetadata = () => remoteVideo.play().catch(() => {});
    }

    updateConnectionStatus(message, isError = false) {
        if (!this.statusElement) {
            return;
        }
        this.statusElement.textContent = message;
        this.statusElement.classList.toggle('text-red-400', isError);
        this.statusElement.classList.toggle('text-white', !isError);
    }

    updateParticipantCount(count) {
        if (!this.participantCountElement) {
            return;
        }
        this.participantCountElement.textContent = `Participants : ${count}`;
    }

    showError(message) {
        if (!this.errorElement) {
            return;
        }
        this.errorElement.textContent = message;
        this.errorElement.classList.remove('hidden');
    }

    showToast(message, isError = false) {
        const toast = document.querySelector('#notificationToast');
        if (!toast) {
            return;
        }
        toast.textContent = message;
        toast.classList.remove('hidden');
        toast.classList.toggle('bg-red-950', isError);
        toast.classList.toggle('bg-[#111117]', !isError);
        setTimeout(() => toast.classList.add('hidden'), 4000);
    }

    generatePeerId() {
        return `${this.currentUser}-${Math.random().toString(36).slice(2, 10)}`;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const conference = new NumeriaConference();
    conference.init();
});
