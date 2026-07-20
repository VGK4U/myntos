/**
 * VGK Assistant — Mobile Component
 * DC_VGK_MOBILE_001: Floating AI assistant for Staff & Partner portals
 */

import { apiService } from '../services/api.service';
import { portalService } from '../services/portal.service';

interface VGKMessage {
  role: 'user' | 'assistant';
  text: string;
}

export class VGKMobileAssistant {
  private container: HTMLElement;
  private fab: HTMLButtonElement | null = null;
  private modal: HTMLElement | null = null;
  private messages: VGKMessage[] = [];
  private conversationHistory: Array<{ role: string; text: string }> = [];
  private isOpen = false;
  private isLoading = false;

  constructor() {
    this.container = document.createElement('div');
    this.container.id = 'vgk-mobile-root';
    document.body.appendChild(this.container);
    this.render();
  }

  private getEndpoint(): string | null {
    const portal = portalService.getPortal();
    if (portal === 'staff') return '/api/v1/vgk/staff/process';
    if (portal === 'partner') return '/api/v1/vgk/partner/process';
    return null;
  }

  private render() {
    const endpoint = this.getEndpoint();
    if (!endpoint) return;

    this.container.innerHTML = `
      <style>
        #vgk-mobile-fab {
          position: fixed; bottom: 80px; right: 16px; z-index: 9999;
          width: 52px; height: 52px; border-radius: 50%;
          background: linear-gradient(135deg, #6c3de8, #a855f7);
          border: none; box-shadow: 0 4px 16px rgba(108,61,232,.5);
          cursor: pointer; display: flex; align-items: center; justify-content: center;
          font-size: 22px; transition: transform .2s;
        }
        #vgk-mobile-fab:active { transform: scale(.92); }
        #vgk-mobile-modal {
          position: fixed; bottom: 0; left: 0; right: 0; z-index: 10000;
          background: #1a1a2e; border-radius: 20px 20px 0 0;
          box-shadow: 0 -4px 32px rgba(0,0,0,.6);
          display: none; flex-direction: column; max-height: 75vh;
          transition: transform .3s;
        }
        #vgk-mobile-modal.open { display: flex; }
        #vgk-modal-header {
          display: flex; align-items: center; gap: 10px;
          padding: 14px 16px 10px; border-bottom: 1px solid #2d2d50;
        }
        #vgk-modal-header img { width: 28px; height: 28px; border-radius: 50%; }
        #vgk-modal-header span { font-weight: 600; color: #e2e8f0; font-size: 15px; flex: 1; }
        #vgk-close-btn {
          background: none; border: none; color: #94a3b8;
          font-size: 20px; cursor: pointer; padding: 4px 8px;
        }
        #vgk-messages {
          flex: 1; overflow-y: auto; padding: 12px 14px;
          display: flex; flex-direction: column; gap: 8px;
        }
        .vgk-bubble {
          max-width: 85%; padding: 9px 13px; border-radius: 16px;
          font-size: 13px; line-height: 1.45; word-break: break-word;
        }
        .vgk-bubble.user {
          background: #6c3de8; color: #fff;
          align-self: flex-end; border-bottom-right-radius: 4px;
        }
        .vgk-bubble.assistant {
          background: #2d2d50; color: #e2e8f0;
          align-self: flex-start; border-bottom-left-radius: 4px;
        }
        .vgk-typing { display: flex; gap: 4px; align-items: center; padding: 10px 14px; }
        .vgk-dot { width: 7px; height: 7px; border-radius: 50%; background: #6c3de8; animation: vgkDot 1.2s infinite; }
        .vgk-dot:nth-child(2) { animation-delay: .2s; }
        .vgk-dot:nth-child(3) { animation-delay: .4s; }
        @keyframes vgkDot { 0%,80%,100%{opacity:.3;transform:scale(.8)} 40%{opacity:1;transform:scale(1)} }
        #vgk-input-row {
          display: flex; align-items: center; gap: 8px;
          padding: 10px 14px; border-top: 1px solid #2d2d50;
        }
        #vgk-text-input {
          flex: 1; background: #2d2d50; border: 1px solid #3d3d70; border-radius: 20px;
          color: #e2e8f0; padding: 8px 14px; font-size: 13px; outline: none;
        }
        #vgk-text-input::placeholder { color: #64748b; }
        #vgk-send-btn, #vgk-mic-btn {
          background: none; border: none; font-size: 20px; cursor: pointer;
          padding: 4px 6px; color: #6c3de8;
        }
        #vgk-mic-btn.recording { color: #ef4444; animation: vgkPulse 1s infinite; }
        @keyframes vgkPulse { 0%,100%{opacity:1} 50%{opacity:.4} }
      </style>

      <button id="vgk-mobile-fab" aria-label="VGK Assistant">
        <img src="/public/vgk-assistant-logo.png" onerror="this.style.display='none';this.parentElement.textContent='🤖'" style="width:30px;height:30px;border-radius:50%;">
      </button>

      <div id="vgk-mobile-modal">
        <div id="vgk-modal-header">
          <img src="/public/vgk-assistant-logo.png" onerror="this.style.display='none'">
          <span>VGK Assistant</span>
          <button id="vgk-close-btn">✕</button>
        </div>
        <div id="vgk-messages"></div>
        <div id="vgk-input-row">
          <input id="vgk-text-input" type="text" placeholder="Ask me anything…" autocomplete="off">
          <button id="vgk-mic-btn" title="Voice input">🎤</button>
          <button id="vgk-send-btn" title="Send">➤</button>
        </div>
      </div>
    `;

    this.fab = this.container.querySelector('#vgk-mobile-fab');
    this.modal = this.container.querySelector('#vgk-mobile-modal');

    this.fab?.addEventListener('click', () => this.open());
    this.container.querySelector('#vgk-close-btn')?.addEventListener('click', () => this.close());

    const input = this.container.querySelector('#vgk-text-input') as HTMLInputElement;
    this.container.querySelector('#vgk-send-btn')?.addEventListener('click', () => {
      if (input.value.trim()) { this.send(input.value.trim()); input.value = ''; }
    });
    input?.addEventListener('keypress', (e: KeyboardEvent) => {
      if (e.key === 'Enter' && input.value.trim()) { this.send(input.value.trim()); input.value = ''; }
    });

    this.container.querySelector('#vgk-mic-btn')?.addEventListener('click', () => this.startVoice(input));

    this.pushMessage('assistant', 'Hi! I\'m VGK Assistant. How can I help you today?');
  }

  private open() {
    this.modal?.classList.add('open');
    this.isOpen = true;
    this.scrollToBottom();
  }

  private close() {
    this.modal?.classList.remove('open');
    this.isOpen = false;
  }

  private pushMessage(role: 'user' | 'assistant', text: string) {
    this.messages.push({ role, text });
    this.renderMessages();
  }

  private renderMessages() {
    const box = this.container.querySelector('#vgk-messages');
    if (!box) return;
    box.innerHTML = this.messages.map(m =>
      `<div class="vgk-bubble ${m.role}">${m.text.replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\n/g,'<br>')}</div>`
    ).join('');
    if (this.isLoading) {
      box.innerHTML += `<div class="vgk-typing"><div class="vgk-dot"></div><div class="vgk-dot"></div><div class="vgk-dot"></div></div>`;
    }
    this.scrollToBottom();
  }

  private scrollToBottom() {
    const box = this.container.querySelector('#vgk-messages');
    if (box) box.scrollTop = box.scrollHeight;
  }

  private async send(text: string) {
    if (this.isLoading) return;
    this.pushMessage('user', text);
    this.isLoading = true;
    this.renderMessages();

    const endpoint = this.getEndpoint();
    if (!endpoint) { this.pushMessage('assistant', 'Not available for this portal.'); this.isLoading = false; return; }

    try {
      const token = await apiService.getToken();
      const resp = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          user_message: text,
          conversation_history: this.conversationHistory.slice(-20),
          language: 'en',
          company_id: null,
          allowed_intents: null,
        })
      });
      const data = await resp.json();
      if (data.reply_text) {
        this.conversationHistory.push({ role: 'user', text });
        this.conversationHistory.push({ role: 'assistant', text: data.reply_text });
        if (this.conversationHistory.length > 20) this.conversationHistory = this.conversationHistory.slice(-20);
        this.pushMessage('assistant', data.reply_text);
        if (data.speak_text && 'speechSynthesis' in window) {
          const utt = new SpeechSynthesisUtterance(data.speak_text);
          utt.lang = 'en-IN'; utt.rate = 1.0;
          window.speechSynthesis.speak(utt);
        }
      } else {
        this.pushMessage('assistant', data.detail || 'Something went wrong.');
      }
    } catch (e) {
      this.pushMessage('assistant', 'Could not reach VGK server. Please try again.');
    }
    this.isLoading = false;
    this.renderMessages();
  }

  private startVoice(input: HTMLInputElement) {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) { alert('Voice input not supported on this device.'); return; }
    const micBtn = this.container.querySelector('#vgk-mic-btn') as HTMLButtonElement;
    const rec = new SR();
    rec.lang = 'en-IN'; rec.continuous = false; rec.interimResults = false;
    rec.onstart = () => micBtn.classList.add('recording');
    rec.onresult = (e: any) => {
      const t = e.results[0][0].transcript;
      input.value = t;
    };
    rec.onend = () => micBtn.classList.remove('recording');
    rec.onerror = () => micBtn.classList.remove('recording');
    rec.start();
  }
}

export function initVGKMobileAssistant(): void {
  const portal = portalService.getPortal();
  if (portal === 'staff' || portal === 'partner') {
    new VGKMobileAssistant();
  }
}
