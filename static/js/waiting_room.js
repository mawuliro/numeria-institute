class WaitingRoomClient {
  constructor() {
    this.roomCode = typeof ROOM_CODE !== 'undefined' ? ROOM_CODE : null;
    this.userName = typeof CURRENT_USER !== 'undefined' ? CURRENT_USER : 'Invité';
    this.wsUrl = typeof WS_URL !== 'undefined' ? WS_URL : null;
    this.ws = null;
    this.shouldReconnect = true;
    this.waitingStatus = document.querySelector('#waiting-status');
    this.waitingDetails = document.querySelector('#waiting-details');
    this.leaveButton = document.querySelector('#btn-leave-waiting');
  }

  init() {
    if (!this.roomCode || !this.wsUrl) {
      this.updateStatus('Le code de réunion est manquant.', true);
      return;
    }
    this.bindEvents();
    this.connectWebSocket();
  }

  bindEvents() {
    this.leaveButton?.addEventListener('click', () => this.leaveWaitingRoom());
  }

  connectWebSocket() {
    if (!this.shouldReconnect) {
      return;
    }
    try {
      this.ws = new WebSocket(this.wsUrl);
      this.ws.addEventListener('open', () => this.onOpen());
      this.ws.addEventListener('message', event => this.onMessage(event));
      this.ws.addEventListener('close', () => this.onClose());
      this.ws.addEventListener('error', () => this.onError());
      this.updateStatus('Connexion à la salle d’attente...', false);
    } catch (error) {
      this.updateStatus('Impossible d’établir la connexion au serveur.', true);
    }
  }

  onOpen() {
    this.send({
      type: 'waiting_request',
      peer_id: `${this.userName}-${Math.random().toString(36).slice(2, 10)}`,
      username: this.userName,
    });
  }

  onMessage(event) {
    let data;
    try {
      data = JSON.parse(event.data);
    } catch (error) {
      return;
    }
    switch (data.type) {
      case 'waiting':
        this.updateStatus(data.message || 'En attente d’admission...', false);
        break;
      case 'admitted':
        this.updateStatus('Admis en réunion... redirection en cours.', false);
        this.shouldReconnect = false;
        if (this.ws) {
          this.ws.close();
        }
        setTimeout(() => {
          window.location.href = `/visio/room/${this.roomCode}/`;
        }, 1200);
        break;
      case 'rejected':
        this.shouldReconnect = false;
        if (this.ws) {
          this.ws.close();
        }
        this.updateStatus(data.message || 'Votre demande a été refusée.', true);
        break;
      case 'meeting_ended':
        this.updateStatus('La réunion a été terminée.', true);
        setTimeout(() => {
          window.location.href = '/';
        }, 2500);
        break;
      case 'error':
        this.updateStatus(data.message || 'Erreur de connexion.', true);
        break;
      default:
        break;
    }
  }

  onClose() {
    if (!this.shouldReconnect) {
      return;
    }
    this.updateStatus('Connexion perdue, reconnexion en cours...', true);
    setTimeout(() => this.connectWebSocket(), 2500);
  }

  onError() {
    this.updateStatus('Erreur WebSocket détectée.', true);
  }

  send(payload) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return;
    }
    this.ws.send(JSON.stringify(payload));
  }

  leaveWaitingRoom() {
    this.shouldReconnect = false;
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.close();
    }
    window.location.href = '/visio/';
  }

  updateStatus(message, isError = false) {
    if (this.waitingStatus) {
      this.waitingStatus.textContent = message;
      this.waitingStatus.classList.toggle('text-red-400', isError);
      this.waitingStatus.classList.toggle('text-teal-300', !isError);
    }
    if (this.waitingDetails) {
      this.waitingDetails.textContent = isError ? 'Actualisez la page ou revenez plus tard.' : 'Restez sur cette page tant que l’hôte prend une décision.';
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const waitingRoom = new WaitingRoomClient();
  waitingRoom.init();
});
