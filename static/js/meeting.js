class NumeriaConference {
  constructor() {
    this.localStream = null;
    this.peerConnections = {};
    this.ws = null;
    this.isMuted = false;
    this.isCameraOff = false;
    this.isScreenSharing = false;
    this.mediaRecorder = null;
    this.recordingChunks = [];
    this.timerInterval = null;
    this.unreadMessages = 0;
    this.localPeerId = this.generatePeerId();
    this.localUserName = typeof CURRENT_USER !== 'undefined' ? CURRENT_USER : 'Invité';
    this.roomCode = typeof ROOM_CODE !== 'undefined' ? ROOM_CODE : null;
    this.wsUrl = typeof WS_URL !== 'undefined' ? WS_URL : null;

    this.statusElement = document.querySelector('#connection-status');
    this.videoCountElement = document.querySelector('#video-count');
    this.chatBadge = document.querySelector('#chatBadge');
    this.chatSidebar = document.querySelector('#chat-sidebar');
    this.participantsSidebar = document.querySelector('#participants-sidebar');
    this.chatFeed = document.querySelector('#chatFeed');
    this.chatInput = document.querySelector('#chat-input');
    this.participantsList = document.querySelector('#participants-list');
    this.localVideoElement = document.querySelector('#local-video');
    this.localCameraOff = document.querySelector('#local-camera-off');
    this.copyRoomCodeButton = document.querySelector('#copyRoomCode');
    this.meetingTimer = document.querySelector('#meeting-timer');
    this.connectionTimer = null;
    this.startTime = null;
  }

  init() {
    if (!this.roomCode || !this.wsUrl) {
      this.showError('Le code de réunion ou l’URL WebSocket est manquant.');
      return;
    }

    this.showStatus('Initialisation de la réunion...', false);
    this.bindGlobalButtons();
    this.checkBrowserSupport();
    this.getUserMedia().finally(() => this.connectWebSocket());
    this.startTimer();
  }

  checkBrowserSupport() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      this.showError('WebRTC non supporté dans ce navigateur. Utilisez Chrome, Firefox, Safari ou Edge récent.');
      throw new Error('WebRTC unsupported');
    }
    if (!window.RTCPeerConnection) {
      this.showError('Votre navigateur ne supporte pas RTCPeerConnection.');
      throw new Error('RTCPeerConnection unsupported');
    }
  }

  async getUserMedia() {
    try {
      this.localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      this.localVideoElement.srcObject = this.localStream;
      this.localVideoElement.play().catch(() => {});
      this.showStatus('Caméra et micro prêts. Connexion au signal...', false);
    } catch (error) {
      console.warn('Erreur getUserMedia:', error);
      try {
        this.localStream = await navigator.mediaDevices.getUserMedia({ video: false, audio: true });
        this.localVideoElement.srcObject = this.localStream;
        this.localVideoElement.play().catch(() => {});
        this.showStatus('Micro actif, caméra désactivée.', true);
        this.isCameraOff = true;
        this.updateLocalCameraState();
      } catch (secondaryError) {
        console.error('Permis refusés ou absence de média:', secondaryError);
        this.showError('Impossible d’accéder à la caméra et au micro. Vérifiez les permissions du navigateur.');
        this.setButtonDisabled('#btn-camera', true);
        this.setButtonDisabled('#btn-mute', true);
        this.showStatus('Média non disponible.', true);
      }
    }
  }

  connectWebSocket() {
    this.showStatus('Connexion WebSocket en cours...', false);
    try {
      this.ws = new WebSocket(this.wsUrl);
      this.ws.addEventListener('open', () => this.onWsOpen());
      this.ws.addEventListener('message', event => this.onWsMessage(event));
      this.ws.addEventListener('close', () => this.onWsClose());
      this.ws.addEventListener('error', () => this.onWsError());
    } catch (error) {
      console.error('Erreur WebSocket:', error);
      this.showError('Impossible d’établir la connexion en temps réel.');
    }
  }

  onWsOpen() {
    this.showStatus('WebSocket connecté ✓', false);
    this.sendMessage({
      type: 'join',
      peer_id: this.localPeerId,
      username: this.localUserName,
      user_id: CURRENT_USER_ID,
    });
  }

  onWsMessage(event) {
    let payload;
    try {
      payload = JSON.parse(event.data);
    } catch (error) {
      console.warn('Message WebSocket invalide:', error, event.data);
      return;
    }
    this.handleSignaling(payload);
  }

  onWsClose() {
    this.showStatus('Connexion WebSocket perdue. Reconnexion...', true);
    setTimeout(() => this.connectWebSocket(), 3000);
  }

  onWsError() {
    this.showStatus('Erreur WebSocket détectée.', true);
  }

  sendMessage(data) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket non prêt pour envoyer:', data);
      return;
    }
    this.ws.send(JSON.stringify(data));
  }

  async handleSignaling(data) {
    switch (data.type) {
      case 'participants_list':
        this.buildParticipants(data.participants || []);
        this.renderChatHistory(data.chat_history || []);
        break;
      case 'user_joined':
        if (data.peer_id === this.localPeerId) return;
        this.addParticipantToSidebar(data.peer_id, data.username);
        if (this.localPeerId < data.peer_id) {
          await this.createPeerConnection(data.peer_id, true);
        } else {
          this.createPeerConnection(data.peer_id, false);
        }
        break;
      case 'user_left':
        this.removeRemoteVideo(data.peer_id);
        this.removeParticipantFromSidebar(data.peer_id);
        break;
      case 'offer':
        if (data.target !== this.localPeerId) return;
        await this.receiveOffer(data);
        break;
      case 'answer':
        if (data.target !== this.localPeerId) return;
        await this.receiveAnswer(data);
        break;
      case 'ice_candidate':
        if (data.target !== this.localPeerId) return;
        await this.addIceCandidate(data);
        break;
      case 'chat':
        this.displayChatMessage(data.sender, data.message, false);
        break;
      case 'raise_hand':
        this.updateParticipantState(data.peer_id, 'hand');
        break;
      case 'mute_status':
        this.updateParticipantState(data.peer_id, 'mute', data.value);
        break;
      case 'camera_status':
        this.updateParticipantState(data.peer_id, 'camera', data.value);
        break;
      case 'meeting_ended':
        this.showToast('La réunion a été terminée par l’hôte.', true);
        setTimeout(() => this.leaveMeeting(), 2500);
        break;
      default:
        console.debug('Signal inconnu reçu:', data);
        break;
    }
  }

  buildParticipants(participants) {
    this.participantsList.innerHTML = '';
    let count = 1;
    participants.forEach(item => {
      if (item.peer_id === this.localPeerId) return;
      this.addParticipantToSidebar(item.peer_id, item.username, item.is_host);
      count += 1;
    });
    this.updateVideoCount(count);
  }

  renderChatHistory(messages) {
    this.chatFeed.innerHTML = '';
    messages.forEach(message => this.displayChatMessage(message.sender, message.message, message.sender === this.localUserName));
  }

  addParticipantToSidebar(peerId, username, isHost = false) {
    if (!this.participantsList) return;
    const existing = this.participantsList.querySelector(`[data-peer-id="${peerId}"]`);
    if (existing) return;
    const item = document.createElement('div');
    item.dataset.peerId = peerId;
    item.className = 'rounded-3xl border border-slate-700 bg-[#020617] p-4';
    item.innerHTML = `<div class="flex items-center justify-between gap-3"><div><p class="font-semibold text-white">${this.escapeHtml(username)}</p><p class="text-xs text-slate-400">${isHost ? 'Hôte' : 'Participant'}</p></div><span id="participant-status-${peerId}" class="text-xs text-teal-300">En ligne</span></div>`;
    this.participantsList.appendChild(item);
    this.updateVideoCount(this.participantsList.childElementCount + 1);
  }

  removeParticipantFromSidebar(peerId) {
    const participant = this.participantsList.querySelector(`[data-peer-id="${peerId}"]`);
    if (participant) {
      participant.remove();
      this.updateVideoCount(this.participantsList.childElementCount + 1);
    }
  }

  async createPeerConnection(peerId, initiator) {
    if (this.peerConnections[peerId]) {
      return this.peerConnections[peerId];
    }

    const configuration = {
      iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        { urls: 'stun:stun1.l.google.com:19302' },
        { urls: 'stun:stun2.l.google.com:19302' },
      ],
    };
    const pc = new RTCPeerConnection(configuration);
    this.peerConnections[peerId] = pc;

    pc.onicecandidate = event => {
      if (event.candidate) {
        this.sendMessage({
          type: 'ice_candidate',
          target: peerId,
          candidate: event.candidate,
        });
      }
    };

    pc.ontrack = event => {
      this.addRemoteVideo(peerId, event.streams[0], 'Participant');
    };

    pc.onconnectionstatechange = () => {
      const state = pc.connectionState;
      const tile = document.querySelector(`#remote-tile-${peerId}`);
      if (tile) {
        tile.dataset.connection = state;
      }
      if (state === 'failed' || state === 'disconnected') {
        this.showToast(`Connexion perdue avec ${peerId}.`, true);
      }
    };

    if (this.localStream) {
      this.localStream.getTracks().forEach(track => pc.addTrack(track, this.localStream));
    }

    if (initiator) {
      await this.createOffer(peerId);
    }

    return pc;
  }

  async createOffer(peerId) {
    const pc = this.peerConnections[peerId];
    if (!pc) return;

    try {
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      this.sendMessage({
        type: 'offer',
        target: peerId,
        sdp: offer.sdp,
      });
    } catch (error) {
      console.error('Erreur création offre:', error);
      this.showError('Impossible de créer l’offre WebRTC.');
    }
  }

  async receiveOffer(data) {
    const peerId = data.from;
    if (!peerId) return;
    const pc = await this.createPeerConnection(peerId, false);
    try {
      await pc.setRemoteDescription({ type: 'offer', sdp: data.sdp });
      const answer = await pc.createAnswer();
      await pc.setLocalDescription(answer);
      this.sendMessage({
        type: 'answer',
        target: peerId,
        sdp: answer.sdp,
      });
    } catch (error) {
      console.error('Erreur réception offre:', error);
      this.showError('Impossible de traiter l’offre entrante.');
    }
  }

  async receiveAnswer(data) {
    const peerId = data.from;
    const pc = this.peerConnections[peerId];
    if (!pc) return;
    try {
      await pc.setRemoteDescription({ type: 'answer', sdp: data.sdp });
    } catch (error) {
      console.error('Erreur réception réponse:', error);
      this.showError('Impossible de traiter la réponse WebRTC.');
    }
  }

  async addIceCandidate(data) {
    const peerId = data.from;
    const pc = this.peerConnections[peerId];
    if (!pc || !data.candidate) return;
    try {
      await pc.addIceCandidate(data.candidate);
    } catch (error) {
      console.warn('Impossible d’ajouter ICE candidate:', error);
    }
  }

  addRemoteVideo(peerId, stream, username = 'Participant') {
    let tile = document.querySelector(`#remote-tile-${peerId}`);
    if (!tile) {
      tile = document.createElement('div');
      tile.id = `remote-tile-${peerId}`;
      tile.className = 'relative overflow-hidden rounded-[2rem] border border-white/10 bg-[#08101F] shadow-inner shadow-black/40';
      tile.innerHTML = `
        <video id="remote-video-${peerId}" autoplay playsinline class="h-full w-full min-h-[220px] object-cover"></video>
        <div class="absolute left-4 bottom-4 rounded-full bg-[#0F766E]/90 px-3 py-1 text-sm font-semibold text-white">${this.escapeHtml(username)}</div>
        <div id="remote-muted-${peerId}" class="absolute right-4 top-4 hidden rounded-full bg-black/70 px-3 py-1 text-xs text-white">🔇</div>
      `;
      document.querySelector('#video-grid')?.appendChild(tile);
      this.updateVideoCount((document.querySelectorAll('#video-grid > div').length || 0) + 1);
    }
    const video = tile.querySelector('video');
    if (video) {
      video.srcObject = stream;
      video.play().catch(() => {});
    }
  }

  removeRemoteVideo(peerId) {
    const tile = document.querySelector(`#remote-tile-${peerId}`);
    if (tile) {
      tile.remove();
      delete this.peerConnections[peerId];
      this.updateVideoCount(Math.max(1, document.querySelectorAll('#video-grid > div').length + 1));
    }
    if (this.peerConnections[peerId]) {
      this.peerConnections[peerId].close();
      delete this.peerConnections[peerId];
    }
  }

  toggleMute() {
    if (!this.localStream) return;
    this.isMuted = !this.isMuted;
    this.localStream.getAudioTracks().forEach(track => track.enabled = !this.isMuted);
    const button = document.querySelector('#btn-mute');
    if (button) {
      button.classList.toggle('bg-red-600', this.isMuted);
      button.textContent = this.isMuted ? '🔇 Micro coupé' : '🎤 Micro actif';
    }
    this.sendMessage({ type: 'mute_status', peer_id: this.localPeerId, value: this.isMuted });
  }

  toggleCamera() {
    if (!this.localStream) return;
    this.isCameraOff = !this.isCameraOff;
    this.localStream.getVideoTracks().forEach(track => track.enabled = !this.isCameraOff);
    const button = document.querySelector('#btn-camera');
    if (button) {
      button.classList.toggle('bg-red-600', this.isCameraOff);
      button.textContent = this.isCameraOff ? '🚫 Vidéo coupée' : '📷 Vidéo active';
    }
    this.updateLocalCameraState();
    this.sendMessage({ type: 'camera_status', peer_id: this.localPeerId, value: !this.isCameraOff });
  }

  updateLocalCameraState() {
    if (!this.localCameraOff) return;
    this.localCameraOff.classList.toggle('hidden', !this.isCameraOff);
  }

  async startScreenShare() {
    if (this.isScreenSharing) {
      return this.stopScreenShare();
    }
    if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
      this.showToast('Partage d’écran non supporté par votre navigateur.', true);
      return;
    }

    try {
      const screenStream = await navigator.mediaDevices.getDisplayMedia({ video: true });
      const screenTrack = screenStream.getVideoTracks()[0];
      const localVideoTrack = this.localStream?.getVideoTracks()[0];

      if (!screenTrack) {
        throw new Error('Aucune piste d’écran disponible.');
      }

      this.isScreenSharing = true;
      document.querySelector('#btn-screen')?.classList.add('bg-teal-500');
      document.querySelector('#btn-screen').textContent = '🛑 Arrêter le partage';
      this.localVideoElement.srcObject = screenStream;
      this.localVideoElement.play().catch(() => {});

      Object.values(this.peerConnections).forEach(pc => {
        const sender = pc.getSenders().find(s => s.track && s.track.kind === 'video');
        if (sender) {
          sender.replaceTrack(screenTrack);
        }
      });

      screenTrack.onended = () => this.stopScreenShare();
    } catch (error) {
      console.error('Erreur partage d’écran:', error);
      this.showError('Impossible de partager l’écran.');
    }
  }

  stopScreenShare() {
    if (!this.isScreenSharing) return;
    const cameraTrack = this.localStream?.getVideoTracks()[0];
    if (!cameraTrack) {
      return;
    }

    Object.values(this.peerConnections).forEach(pc => {
      const sender = pc.getSenders().find(s => s.track && s.track.kind === 'video');
      if (sender) {
        sender.replaceTrack(cameraTrack);
      }
    });
    this.localVideoElement.srcObject = this.localStream;
    this.localVideoElement.play().catch(() => {});
    this.isScreenSharing = false;
    const button = document.querySelector('#btn-screen');
    if (button) {
      button.classList.remove('bg-teal-500');
      button.textContent = '🖥️ Partager l’écran';
    }
  }

  toggleChat() {
    if (!this.chatSidebar) return;
    this.chatSidebar.classList.toggle('hidden');
    if (!this.chatSidebar.classList.contains('hidden')) {
      this.unreadMessages = 0;
      this.updateChatBadge();
    }
  }

  toggleParticipants() {
    if (!this.participantsSidebar) return;
    this.participantsSidebar.classList.toggle('hidden');
  }

  async sendChatMessage() {
    const content = this.chatInput.value.trim();
    if (!content) return;
    this.sendMessage({ type: 'chat', message: content });
    this.displayChatMessage(this.localUserName, content, true);
    this.chatInput.value = '';
  }

  displayChatMessage(username, message, isLocal) {
    if (!this.chatFeed) return;
    const line = document.createElement('div');
    line.className = `rounded-3xl px-4 py-3 ${isLocal ? 'bg-teal-500/15 text-white' : 'bg-white/5 text-slate-200'}`;
    line.innerHTML = `<p class="text-xs text-slate-400">${this.escapeHtml(username)}</p><p class="mt-1 text-sm">${this.escapeHtml(message)}</p>`;
    this.chatFeed.appendChild(line);
    this.chatFeed.scrollTop = this.chatFeed.scrollHeight;
    if (this.chatSidebar && this.chatSidebar.classList.contains('hidden')) {
      this.unreadMessages += 1;
      this.updateChatBadge();
    }
  }

  updateChatBadge() {
    if (!this.chatBadge) return;
    if (this.unreadMessages > 0) {
      this.chatBadge.classList.remove('hidden');
      this.chatBadge.textContent = this.unreadMessages;
    } else {
      this.chatBadge.classList.add('hidden');
    }
  }

  updateParticipantState(peerId, kind, value) {
    const participant = this.participantsList.querySelector(`[data-peer-id="${peerId}"]`);
    if (!participant) return;
    let statusLabel = participant.querySelector(`#participant-status-${peerId}`);
    if (!statusLabel) return;

    if (kind === 'hand') {
      statusLabel.textContent = 'Main levée';
    }
    if (kind === 'mute') {
      statusLabel.textContent = value ? 'Muet' : 'Micro actif';
    }
    if (kind === 'camera') {
      statusLabel.textContent = value ? 'Vidéo active' : 'Vidéo coupée';
      const tile = document.querySelector(`#remote-tile-${peerId}`);
      if (tile) {
        tile.classList.toggle('opacity-50', !value);
      }
    }
  }

  startTimer() {
    if (this.timerInterval) return;
    this.startTime = Date.now();
    this.timerInterval = setInterval(() => {
      const seconds = Math.floor((Date.now() - this.startTime) / 1000);
      const hh = String(Math.floor(seconds / 3600)).padStart(2, '0');
      const mm = String(Math.floor((seconds % 3600) / 60)).padStart(2, '0');
      const ss = String(seconds % 60).padStart(2, '0');
      if (this.meetingTimer) {
        this.meetingTimer.textContent = `${hh}:${mm}:${ss}`;
      }
    }, 1000);
  }

  updateVideoCount(count) {
    if (!this.videoCountElement) return;
    this.videoCountElement.textContent = count.toString();
  }

  async leaveMeeting() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.sendMessage({ type: 'leave', peer_id: this.localPeerId });
      this.ws.close();
    }
    if (this.localStream) {
      this.localStream.getTracks().forEach(track => track.stop());
    }
    Object.values(this.peerConnections).forEach(pc => {
      pc.close();
    });
    window.location.href = '/visio/';
  }

  async endMeeting() {
    if (!IS_HOST) {
      this.showToast('Seul l’hôte peut terminer la réunion.', true);
      return;
    }
    try {
      const response = await fetch(`/visio/room/${this.roomCode}/end/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'X-CSRFToken': this.getCsrfToken(),
        },
        body: '',
      });
      if (response.ok) {
        this.showToast('Réunion terminée pour tous.', false);
        this.leaveMeeting();
      } else {
        this.showError('Impossible de terminer la réunion.');
      }
    } catch (error) {
      console.error('Erreur end meeting:', error);
      this.showError('Erreur réseau lors de la fin de réunion.');
    }
  }

  bindGlobalButtons() {
    document.querySelector('#btn-mute')?.addEventListener('click', () => this.toggleMute());
    document.querySelector('#btn-camera')?.addEventListener('click', () => this.toggleCamera());
    document.querySelector('#btn-screen')?.addEventListener('click', () => this.startScreenShare());
    document.querySelector('#btn-chat')?.addEventListener('click', () => this.toggleChat());
    document.querySelector('#btn-participants')?.addEventListener('click', () => this.toggleParticipants());
    document.querySelector('#btn-hand')?.addEventListener('click', () => this.sendMessage({ type: 'raise_hand', peer_id: this.localPeerId }));
    document.querySelector('#btn-record')?.addEventListener('click', () => this.toggleRecording());
    document.querySelector('#btn-leave')?.addEventListener('click', () => this.leaveMeeting());
    document.querySelector('#btn-end')?.addEventListener('click', () => this.endMeeting());
    document.querySelector('#chat-send')?.addEventListener('click', () => this.sendChatMessage());
    this.chatInput?.addEventListener('keydown', event => {
      if (event.key === 'Enter') {
        event.preventDefault();
        this.sendChatMessage();
      }
    });
    this.copyRoomCodeButton?.addEventListener('click', () => {
      navigator.clipboard.writeText(this.roomCode).then(() => {
        this.showToast('Code de réunion copié');
      }).catch(() => {
        this.showToast('Impossible de copier le code', true);
      });
    });
  }

  toggleRecording() {
    if (!this.localStream) {
      this.showToast('Aucun flux disponible pour l’enregistrement.', true);
      return;
    }
    if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
      this.mediaRecorder.stop();
      return;
    }
    try {
      this.mediaRecorder = new MediaRecorder(this.localStream);
      this.recordingChunks = [];
      this.mediaRecorder.addEventListener('dataavailable', event => {
        if (event.data.size > 0) {
          this.recordingChunks.push(event.data);
        }
      });
      this.mediaRecorder.addEventListener('stop', () => {
        const blob = new Blob(this.recordingChunks, { type: 'video/webm' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'numeria-reunion.webm';
        a.click();
        URL.revokeObjectURL(url);
        this.showToast('Enregistrement disponible en téléchargement.');
      });
      this.mediaRecorder.start();
      this.showToast('Enregistrement démarré.');
    } catch (error) {
      console.error('MediaRecorder error:', error);
      this.showToast('Impossible de démarrer l’enregistrement.', true);
    }
  }

  getCsrfToken() {
    const name = 'csrftoken';
    const cookies = document.cookie.split(';');
    for (const cookie of cookies) {
      const [key, value] = cookie.trim().split('=');
      if (key === name) {
        return decodeURIComponent(value);
      }
    }
    return '';
  }

  showStatus(message, isError = false) {
    if (!this.statusElement) return;
    this.statusElement.textContent = message;
    this.statusElement.classList.toggle('text-red-400', isError);
    this.statusElement.classList.toggle('text-teal-300', !isError);
  }

  showError(message) {
    this.showStatus(message, true);
    this.showToast(message, true);
  }

  showToast(message, isError = false) {
    const toast = document.createElement('div');
    toast.textContent = message;
    toast.className = `fixed bottom-6 right-6 z-50 rounded-3xl px-5 py-3 text-sm text-white shadow-2xl ${isError ? 'bg-red-600' : 'bg-slate-900'}`;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3200);
  }

  escapeHtml(value) {
    const div = document.createElement('div');
    div.textContent = value;
    return div.innerHTML;
  }

  setButtonDisabled(selector, disabled) {
    const button = document.querySelector(selector);
    if (button) {
      button.disabled = disabled;
      button.classList.toggle('opacity-50', disabled);
      button.classList.toggle('cursor-not-allowed', disabled);
    }
  }

  generatePeerId() {
    return `${this.localUserName}-${Math.random().toString(36).slice(2, 10)}`;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const conference = new NumeriaConference();
  conference.init();
});
