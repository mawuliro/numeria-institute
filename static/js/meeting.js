class NumeriaConference {
  constructor() {
    this.localStream = null;
    this.screenStream = null;
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
    this.waitingQueue = document.querySelector('#waiting-queue');
    this.waitingCount = document.querySelector('#waiting-count');
    this.localVideoElement = document.querySelector('#local-video');
    this.localCameraOff = document.querySelector('#local-camera-off');
    this.copyRoomCodeButton = document.querySelector('#copyRoomCode');
    this.meetingTimer = document.querySelector('#meeting-timer');
    this.connectionTimer = null;
    this.startTime = null;
    this.shouldReconnect = true;
    this.screenShareTrack = null;
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
    if (!this.shouldReconnect) {
      return;
    }
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
    if (!this.shouldReconnect) {
      this.showStatus('Connexion fermée.', true);
      return;
    }
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
        await this.processParticipants(data.participants || []);
        this.renderChatHistory(data.chat_history || []);
        break;
      case 'user_joined':
        if (data.peer_id === this.localPeerId) return;
        this.addParticipantToSidebar(data.peer_id, data.username, data.is_host);
        await this.createPeerConnection(data.peer_id, false);
        break;
      case 'user_left':
        this.removeRemoteVideo(data.peer_id);
        this.removeParticipantFromSidebar(data.peer_id);
        break;
      case 'mute_all':
        this.setLocalMute(true, true);
        this.showToast('L’hôte a coupé le micro de tous.');
        break;
      case 'camera_off_all':
        this.setLocalCamera(false, true);
        this.showToast('L’hôte a coupé la caméra de tous.');
        break;
      case 'waiting_list':
        if (IS_HOST) {
          this.renderWaitingList(data.waiting || []);
        }
        break;
      case 'admitted':
        if (data.target === undefined || data.target === this.localPeerId) {
          this.showToast('Vous avez été admis·e en réunion.', false);
          setTimeout(() => {
            window.location.reload();
          }, 800);
        }
        break;
      case 'rejected':
        if (data.target === undefined || data.target === this.localPeerId) {
          this.showError(data.message || 'Votre participation a été refusée.');
          setTimeout(() => {
            window.location.href = '/visio/';
          }, 2000);
        }
        break;
      case 'removed':
        if (data.target === undefined || data.target === this.localPeerId) {
          this.showToast(data.message || 'Vous avez été retiré·e par l’hôte.', true);
          setTimeout(() => this.leaveMeeting(), 1200);
        }
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
      case 'error':
        this.showError(data.message || 'Erreur de réunion.');
        break;
      default:
        console.debug('Signal inconnu reçu:', data);
        break;
    }
  }

  async processParticipants(participants) {
    if (!this.participantsList) return;
    this.participantsList.innerHTML = '';
    const remoteParticipants = [];

    participants.forEach(item => {
      if (item.peer_id === this.localPeerId) return;
      this.addParticipantToSidebar(item.peer_id, item.username, item.is_host);
      remoteParticipants.push(item);
    });
    this.updateVideoCount(remoteParticipants.length + 1);

    await Promise.all(remoteParticipants.map(item => this.createPeerConnection(item.peer_id, true)));
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
    item.className = 'flex items-center justify-between gap-3 rounded-xl px-3 py-2.5 bg-[#0B1120] border border-slate-700/40';
    const initial = (username || '?').charAt(0).toUpperCase();
    item.innerHTML = `
      <div class="flex items-center gap-3 min-w-0">
        <div class="w-9 h-9 rounded-full ${isHost ? 'bg-numeria-or/20 text-numeria-or' : 'bg-numeria-teal/20 text-numeria-teal'} flex items-center justify-center text-sm font-bold flex-shrink-0" style="font-family:'Outfit',sans-serif;">
          ${this.escapeHtml(initial)}
        </div>
        <div class="min-w-0">
          <p class="text-sm font-semibold text-white truncate">${this.escapeHtml(username)}</p>
          <p class="text-[10px] text-slate-400 uppercase tracking-wider">${isHost ? 'Hôte' : 'Participant'}</p>
        </div>
      </div>
      <div class="flex items-center gap-2 flex-shrink-0">
        <span id="participant-status-${peerId}" class="text-[10px] text-emerald-400 uppercase tracking-wider">En ligne</span>
        ${IS_HOST && !isHost ? `<button type="button" data-remove-participant="${this.escapeHtml(peerId)}" class="w-7 h-7 rounded-full bg-red-500/10 hover:bg-red-500/20 text-red-400 flex items-center justify-center transition" title="Retirer" aria-label="Retirer ce participant">
          <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>` : ''}
      </div>
    `;
    this.participantsList.appendChild(item);
    this.updateVideoCount();
  }

  renderWaitingList(waiting) {
    if (!this.waitingQueue) return;
    this.waitingQueue.innerHTML = '';
    waiting.forEach(item => {
      const row = document.createElement('div');
      row.dataset.peerId = item.peer_id;
      row.className = 'rounded-3xl border border-slate-700 bg-[#020617] p-4 flex items-center justify-between gap-3';
      row.innerHTML = `
        <div>
          <p class="font-semibold text-white">${this.escapeHtml(item.username)}</p>
          <p class="text-xs text-slate-400">En attente d’admission</p>
        </div>
        <div class="flex gap-2">
          <button data-admit-participant="${this.escapeHtml(item.peer_id)}" class="rounded-3xl bg-teal-500 px-3 py-2 text-xs font-semibold text-slate-950">Admettre</button>
          <button data-reject-participant="${this.escapeHtml(item.peer_id)}" class="rounded-3xl bg-red-600 px-3 py-2 text-xs font-semibold text-white">Rejeter</button>
        </div>
      `;
      this.waitingQueue.appendChild(row);
    });
    this.updateWaitingCount(waiting.length);
  }

  updateWaitingCount(count) {
    if (!this.waitingCount) return;
    this.waitingCount.textContent = count.toString();
  }

  removeParticipantFromSidebar(peerId) {
    const participant = this.participantsList.querySelector(`[data-peer-id="${peerId}"]`);
    if (participant) {
      participant.remove();
      this.updateVideoCount();
    }
    if (this.peerConnections[peerId]) {
      this.peerConnections[peerId].close();
      delete this.peerConnections[peerId];
    }
  }

  admitParticipant(peerId) {
    this.sendMessage({ type: 'admit_participant', target: peerId });
  }

  rejectParticipant(peerId) {
    this.sendMessage({ type: 'reject_participant', target: peerId });
  }

  removeParticipant(peerId) {
    this.sendMessage({ type: 'remove_participant', target: peerId });
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
      if (this.isScreenSharing && this.screenStream) {
        const sharedVideoTrack = this.screenStream.getVideoTracks()[0];
        if (sharedVideoTrack) {
          pc.addTrack(sharedVideoTrack, this.screenStream);
        }
        this.localStream.getAudioTracks().forEach(track => pc.addTrack(track, this.localStream));
      } else {
        this.localStream.getTracks().forEach(track => pc.addTrack(track, this.localStream));
      }
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
      tile.className = 'relative overflow-hidden rounded-2xl border border-white/10 bg-[#131826] shadow-lg shadow-black/30 aspect-video min-h-[200px]';
      tile.innerHTML = `
        <video id="remote-video-${peerId}" autoplay playsinline class="absolute inset-0 w-full h-full object-cover"></video>
        <div class="absolute inset-0 hidden items-center justify-center bg-[#1A2235]" id="remote-camera-off-${peerId}">
          <div class="w-16 h-16 rounded-full bg-slate-700 flex items-center justify-center text-xl font-bold text-white" style="font-family:'Outfit',sans-serif;">${this.escapeHtml(username.charAt(0).toUpperCase())}</div>
        </div>
        <div class="absolute bottom-2 left-2 right-2 flex items-center justify-between gap-2 pointer-events-none">
          <div class="bg-black/70 backdrop-blur-sm rounded-full px-2.5 py-1 text-xs font-medium text-white truncate max-w-[80%]">${this.escapeHtml(username)}</div>
          <div id="remote-muted-${peerId}" class="hidden w-6 h-6 rounded-full bg-red-500/80 backdrop-blur-sm flex items-center justify-center flex-shrink-0">
            <svg class="w-3 h-3 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <line x1="1" y1="1" x2="23" y2="23"/>
              <path d="M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V4a3 3 0 0 0-5.94-.6"/>
              <path d="M17 16.95A7 7 0 0 1 5 12v-2m14 0v2a7 7 0 0 1-.11 1.23"/>
            </svg>
          </div>
        </div>
      `;
      document.querySelector('#video-grid')?.appendChild(tile);
      this.updateVideoCount();
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
      this.updateVideoCount();
    }
    if (this.peerConnections[peerId]) {
      this.peerConnections[peerId].close();
      delete this.peerConnections[peerId];
    }
  }

  toggleMute() {
    if (!this.localStream) return;
    this.setLocalMute(!this.isMuted, true);
  }

  toggleCamera() {
    if (!this.localStream) return;
    this.setLocalCamera(this.isCameraOff, true);
  }

  updateLocalCameraState() {
    if (!this.localCameraOff) return;
    // Use 'flex' / 'hidden' so the overlay's inner flex centering works
    if (this.isCameraOff) {
      this.localCameraOff.classList.remove('hidden');
      this.localCameraOff.classList.add('flex');
    } else {
      this.localCameraOff.classList.add('hidden');
      this.localCameraOff.classList.remove('flex');
    }
  }

  setLocalMute(muted, notify = false) {
    if (!this.localStream) return;
    this.isMuted = muted;
    this.localStream.getAudioTracks().forEach(track => track.enabled = !this.isMuted);
    const button = document.querySelector('#btn-mute');
    if (button) {
      // Swap mic icon (svg.mic-on / svg.mic-off)
      const micOn = button.querySelector('.mic-on');
      const micOff = button.querySelector('.mic-off');
      if (micOn && micOff) {
        micOn.classList.toggle('hidden', this.isMuted);
        micOff.classList.toggle('hidden', !this.isMuted);
      }
      button.classList.toggle('bg-red-500', this.isMuted);
      button.classList.toggle('hover:bg-red-600', this.isMuted);
      button.classList.toggle('bg-[#1A2235]', !this.isMuted);
      button.classList.toggle('hover:bg-[#243049]', !this.isMuted);
    }
    // Update local mic badge in self-view
    const micBadge = document.querySelector('#local-mic-badge');
    if (micBadge) {
      micBadge.classList.toggle('bg-red-500/80', this.isMuted);
      micBadge.classList.toggle('bg-black/70', !this.isMuted);
    }
    if (notify) {
      this.sendMessage({ type: 'mute_status', peer_id: this.localPeerId, value: this.isMuted });
    }
  }

  setLocalCamera(enabled, notify = false) {
    if (!this.localStream) return;
    this.isCameraOff = !enabled;
    this.localStream.getVideoTracks().forEach(track => track.enabled = enabled);
    this.updateLocalCameraState();
    const button = document.querySelector('#btn-camera');
    if (button) {
      // Swap camera icon (svg.cam-on / svg.cam-off)
      const camOn = button.querySelector('.cam-on');
      const camOff = button.querySelector('.cam-off');
      if (camOn && camOff) {
        camOn.classList.toggle('hidden', this.isCameraOff);
        camOff.classList.toggle('hidden', !this.isCameraOff);
      }
      button.classList.toggle('bg-red-500', this.isCameraOff);
      button.classList.toggle('hover:bg-red-600', this.isCameraOff);
      button.classList.toggle('bg-[#1A2235]', !this.isCameraOff);
      button.classList.toggle('hover:bg-[#243049]', !this.isCameraOff);
    }
    if (!enabled && this.isScreenSharing) {
      this.stopScreenShare();
    }
    if (notify) {
      this.sendMessage({ type: 'camera_status', peer_id: this.localPeerId, value: enabled });
    }
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
      const cameraTrack = this.localStream?.getVideoTracks()[0];

      if (!screenTrack) {
        throw new Error('Aucune piste d’écran disponible.');
      }

      this.isScreenSharing = true;
      this.screenStream = screenStream;
      this.screenShareTrack = screenTrack;
      const screenBtn = document.querySelector('#btn-screen');
      if (screenBtn) {
        screenBtn.classList.add('bg-numeria-teal', 'text-[#0B0F1A]');
        screenBtn.classList.remove('bg-[#1A2235]', 'text-white');
        screenBtn.title = 'Arrêter le partage';
      }
      this.hideScreenSharePreview();
      if (this.localStream) {
        this.localVideoElement.srcObject = this.localStream;
        this.localVideoElement.play().catch(() => {});
      }

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

    if (this.screenShareTrack) {
      this.screenShareTrack.stop();
      this.screenShareTrack = null;
    }

    if (this.screenStream) {
      this.screenStream.getTracks().forEach(track => track.stop());
      this.screenStream = null;
    }

    if (cameraTrack) {
      Object.values(this.peerConnections).forEach(pc => {
        const sender = pc.getSenders().find(s => s.track && s.track.kind === 'video');
        if (sender) {
          sender.replaceTrack(cameraTrack);
        }
      });
    }

    this.localVideoElement.srcObject = this.localStream;
    this.localVideoElement.play().catch(() => {});
    this.isScreenSharing = false;
    this.showScreenSharePreview();
    const button = document.querySelector('#btn-screen');
    if (button) {
      button.classList.remove('bg-numeria-teal', 'text-[#0B0F1A]');
      button.classList.add('bg-[#1A2235]', 'text-white');
      button.title = 'Partager l\'écran';
    }
  }

  hideScreenSharePreview() {
    // Hide the video grid (other participants' tiles) while screen-sharing.
    // Keep the local self-view visible so the sharer still sees themselves.
    document.querySelector('#video-grid')?.classList.add('hidden');
  }

  showScreenSharePreview() {
    document.querySelector('#video-grid')?.classList.remove('hidden');
  }

  toggleChat() {
    if (!this.chatSidebar) return;
    // Use the same hidden/flex toggle pattern as the template's close button.
    // Also close the participants sidebar if open (Meet-style: only one panel at a time).
    if (this.chatSidebar.classList.contains('hidden')) {
      this.chatSidebar.classList.remove('hidden');
      this.chatSidebar.classList.add('flex');
      // Close participants
      this.participantsSidebar?.classList.add('hidden');
      this.participantsSidebar?.classList.remove('flex');
      this.unreadMessages = 0;
      this.updateChatBadge();
      // Clear the floating chat badge too
      document.querySelector('#chatBtnBadge')?.classList.add('hidden');
    } else {
      this.chatSidebar.classList.add('hidden');
      this.chatSidebar.classList.remove('flex');
    }
  }

  toggleParticipants() {
    if (!this.participantsSidebar) return;
    if (this.participantsSidebar.classList.contains('hidden')) {
      this.participantsSidebar.classList.remove('hidden');
      this.participantsSidebar.classList.add('flex');
      // Close chat
      this.chatSidebar?.classList.add('hidden');
      this.chatSidebar?.classList.remove('flex');
    } else {
      this.participantsSidebar.classList.add('hidden');
      this.participantsSidebar.classList.remove('flex');
    }
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
    line.className = `flex flex-col ${isLocal ? 'items-end' : 'items-start'}`;
    const initial = (username || '?').charAt(0).toUpperCase();
    line.innerHTML = `
      <div class="flex items-center gap-2 mb-1 ${isLocal ? 'flex-row-reverse' : ''}">
        <div class="w-5 h-5 rounded-full ${isLocal ? 'bg-numeria-teal/20 text-numeria-teal' : 'bg-slate-700 text-slate-300'} flex items-center justify-center text-[10px] font-bold" style="font-family:'Outfit',sans-serif;">${this.escapeHtml(initial)}</div>
        <span class="text-[11px] font-medium ${isLocal ? 'text-numeria-teal' : 'text-slate-400'}">${this.escapeHtml(username)}</span>
      </div>
      <div class="${isLocal ? 'bg-numeria-teal/15 text-white' : 'bg-white/5 text-slate-200'} rounded-2xl px-3 py-2 text-sm max-w-[85%] break-words">${this.escapeHtml(message)}</div>
    `;
    this.chatFeed.appendChild(line);
    this.chatFeed.scrollTop = this.chatFeed.scrollHeight;
    if (this.chatSidebar && this.chatSidebar.classList.contains('hidden')) {
      this.unreadMessages += 1;
      this.updateChatBadge();
    }
  }

  updateChatBadge() {
    // Update the in-sidebar badge (#chatBadge) AND the floating
    // control-button badge (#chatBtnBadge) so unread messages are
    // visible even when the chat panel is closed.
    const badges = [
      document.querySelector('#chatBadge'),
      document.querySelector('#chatBtnBadge'),
    ];
    badges.forEach(badge => {
      if (!badge) return;
      if (this.unreadMessages > 0) {
        badge.classList.remove('hidden');
        badge.textContent = this.unreadMessages;
        // Ensure it's display-flex if it was hidden via 'hidden' class
        if (badge.id === 'chatBtnBadge') {
          badge.classList.add('flex');
        }
      } else {
        badge.classList.add('hidden');
        if (badge.id === 'chatBtnBadge') {
          badge.classList.remove('flex');
        }
      }
    });
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
      // Toggle the muted indicator in the remote video tile
      const mutedIndicator = document.querySelector(`#remote-muted-${peerId}`);
      if (mutedIndicator) {
        if (value) {
          mutedIndicator.classList.remove('hidden');
          mutedIndicator.classList.add('flex');
        } else {
          mutedIndicator.classList.add('hidden');
          mutedIndicator.classList.remove('flex');
        }
      }
    }
    if (kind === 'camera') {
      statusLabel.textContent = value ? 'Vidéo active' : 'Vidéo coupée';
      // Toggle the camera-off overlay in the remote video tile
      const tile = document.querySelector(`#remote-tile-${peerId}`);
      const cameraOffOverlay = document.querySelector(`#remote-camera-off-${peerId}`);
      if (cameraOffOverlay) {
        if (value) {
          cameraOffOverlay.classList.add('hidden');
          cameraOffOverlay.classList.remove('flex');
        } else {
          cameraOffOverlay.classList.remove('hidden');
          cameraOffOverlay.classList.add('flex');
        }
      }
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
    if (typeof count === 'undefined' || count === null) {
      count = 1 + (document.querySelectorAll('#video-grid > div').length || 0);
    }
    this.videoCountElement.textContent = count.toString();
  }

  async leaveMeeting() {
    this.shouldReconnect = false;
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

  async muteAll() {
    if (!IS_HOST) {
      this.showToast('Seul l’hôte peut couper tous les micros.', true);
      return;
    }
    this.sendMessage({ type: 'mute_all' });
  }

  async cameraOffAll() {
    if (!IS_HOST) {
      this.showToast('Seul l’hôte peut couper toutes les caméras.', true);
      return;
    }
    this.sendMessage({ type: 'camera_off_all' });
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
        this.shouldReconnect = false;
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
    document.querySelector('#btn-mute-all')?.addEventListener('click', () => this.muteAll());
    document.querySelector('#btn-camera-all')?.addEventListener('click', () => this.cameraOffAll());
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

    document.body.addEventListener('click', event => {
      const admitButton = event.target.closest('[data-admit-participant]');
      const rejectButton = event.target.closest('[data-reject-participant]');
      const removeButton = event.target.closest('[data-remove-participant]');
      if (admitButton) {
        this.admitParticipant(admitButton.dataset.admitParticipant);
      }
      if (rejectButton) {
        this.rejectParticipant(rejectButton.dataset.rejectParticipant);
      }
      if (removeButton) {
        this.removeParticipant(removeButton.dataset.removeParticipant);
      }
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
