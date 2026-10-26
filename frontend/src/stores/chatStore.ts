import { create } from 'zustand';
import { apiClient } from '@/lib/api';
import { supabase } from '@/lib/supabase';

export interface ChatMessage {
  id: string;
  chat_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  image_urls?: string[];
  created_at: string;
  // Goldmine metadata (only on assistant messages)
  model_id?: string;
  provider?: string;
  goldmine_score?: number;
  evaluation_signals?: Record<string, number>;
  selection_explanation?: string;
  all_responses?: ModelResponseItem[];
  web_verified?: boolean;
  response_type?: 'model' | 'synthesis' | 'failed';
  provider_failures?: Array<{ model_id: string; provider: string; category: string; phase?: string }>;
  sources?: Array<{ title: string; url: string; domain: string }>;
  attachments?: AttachmentData[];
  web_research?: boolean;
}

export interface AttachmentData {
  id: string;
  file_name: string;
  mime_type: string;
  size_bytes: number;
  temporary?: boolean;
}

export interface SendResult {
  chatId: string | null;
  success: boolean;
}

export type ExperienceMode = 'normal' | 'study' | 'research';

export interface ModelResponseItem {
  id: string;
  model_id: string;
  provider: string;
  content: string;
  goldmine_score: number | null;
  evaluation_signals: Record<string, number> | null;
  selected: boolean;
  latency_ms: number | null;
  web_verified: boolean;
  response_type?: 'model' | 'synthesis' | 'failed';
}

export interface Chat {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

interface ChatState {
  chats: Chat[];
  currentChatId: string | null;
  messages: ChatMessage[];
  isGenerating: boolean;
  modelMode: 'auto' | string; // 'auto' or a specific model_id
  experienceMode: ExperienceMode;
  loadingChats: boolean;
  streamStatus: string;

  loadChats: () => Promise<void>;
  createChat: (title?: string) => Promise<string | null>;
  selectChat: (chatId: string) => Promise<void>;
  deleteChat: (chatId: string) => Promise<boolean>;
  renameChat: (chatId: string, title: string) => Promise<boolean>;
  sendMessage: (content: string, attachments?: AttachmentData[], webResearch?: boolean) => Promise<SendResult>;
  cancelGeneration: () => void;
  setModelMode: (mode: string) => void;
  setExperienceMode: (mode: ExperienceMode) => void;
  clearCurrentChat: () => void;
}

async function getToken() {
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? '';
}

const pendingRequests = new Map<string, string>();
const activeControllers = new Map<string, AbortController>();

async function readEventStream(response: Response, onEvent: (event: any) => void): Promise<any> {
  if (!response.body) throw new Error('The streaming response had no body');
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let complete: any = null;
  const consumeBlock = (block: string) => {
    const data = block.split(/\r?\n/).filter((line) => line.startsWith('data:')).map((line) => line.slice(5).trimStart()).join('\n');
    if (!data) return;
    let event: any;
    try {
      event = JSON.parse(data);
    } catch {
      // Ignore malformed intermediary SSE frames; the final frame is required below.
      return;
    }
    if (event.event === 'error') throw new Error(event.data?.detail || 'The response failed');
    if (event.event === 'complete') complete = event.data;
    else onEvent(event.data);
  };
  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    let separator = buffer.search(/\r?\n\r?\n/);
    while (separator >= 0) {
      const block = buffer.slice(0, separator);
      const match = buffer.slice(separator).match(/^\r?\n\r?\n/);
      buffer = buffer.slice(separator + (match?.[0].length ?? 2));
      consumeBlock(block);
      separator = buffer.search(/\r?\n\r?\n/);
    }
    if (done) break;
  }
  if (buffer.trim()) consumeBlock(buffer);
  if (!complete) throw new Error('The response stream ended before it completed');
  return complete;
}

export const useChatStore = create<ChatState>((set, get) => ({
  chats: [],
  currentChatId: null,
  messages: [],
  isGenerating: false,
  modelMode: 'auto',
  experienceMode: 'normal',
  loadingChats: false,
  streamStatus: '',

  loadChats: async () => {
    set({ loadingChats: true });
    try {
      const token = await getToken();
      const data = await apiClient('/api/chats', { token });
      set({ chats: data, loadingChats: false });
    } catch (e) {
      console.error('Failed to load chats:', e);
      set({ loadingChats: false });
    }
  },

  createChat: async (title?: string) => {
    try {
      const token = await getToken();
      const data = await apiClient('/api/chats', {
        method: 'POST',
        token,
        body: JSON.stringify({ title: title || 'New Chat' }),
      });
      set((s) => ({ chats: [data, ...s.chats], currentChatId: data.id, messages: [] }));
      return data.id;
    } catch (e) {
      console.error('Failed to create chat:', e);
      return null;
    }
  },

  selectChat: async (chatId: string) => {
    set({ currentChatId: chatId, messages: [], isGenerating: pendingRequests.has(chatId), streamStatus: '' });
    try {
      const token = await getToken();
      const data = await apiClient(`/api/chats/${chatId}`, { token });
      if (get().currentChatId === chatId) set({ messages: data.messages || [] });
    } catch (e) {
      console.error('Failed to load chat messages:', e);
    }
  },

  deleteChat: async (chatId: string) => {
    try {
      const token = await getToken();
      await apiClient(`/api/chats/${chatId}`, { method: 'DELETE', token });
      set((s) => ({
        chats: s.chats.filter((c) => c.id !== chatId),
        currentChatId: s.currentChatId === chatId ? null : s.currentChatId,
        messages: s.currentChatId === chatId ? [] : s.messages,
      }));
      return true;
    } catch (e) {
      console.error('Failed to delete chat:', e);
      return false;
    }
  },

  renameChat: async (chatId: string, title: string) => {
    try {
      const token = await getToken();
      await apiClient(`/api/chats/${chatId}`, {
        method: 'PATCH',
        token,
        body: JSON.stringify({ title }),
      });
      set((s) => ({
        chats: s.chats.map((c) => (c.id === chatId ? { ...c, title } : c)),
      }));
      return true;
    } catch (e) {
      console.error('Failed to rename chat:', e);
      return false;
    }
  },

  sendMessage: async (content: string, attachments?: AttachmentData[], webResearch = false) => {
    const state = get();
    let chatId = state.currentChatId;

    // Auto-create chat if needed
    if (!chatId) {
      chatId = await get().createChat(content.slice(0, 50));
      if (!chatId) return { chatId: null, success: false };
    }

    const requestId = crypto.randomUUID();
    pendingRequests.set(chatId, requestId);
    const controller = new AbortController();
    activeControllers.set(chatId, controller);

    // Optimistic user message
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      chat_id: chatId,
      role: 'user',
      content,
      attachments,
      web_research: webResearch,
      created_at: new Date().toISOString(),
    };

    set((s) => ({
      messages: [...s.messages, userMsg],
      isGenerating: true,
      streamStatus: 'Starting response…',
    }));

    try {
      const token = await getToken();
      const modelMode = get().modelMode;

      const response = await apiClient('/api/chat/stream', {
        method: 'POST',
        token,
        signal: controller.signal,
        body: JSON.stringify({
          content,
          chat_id: chatId,
          attachment_ids: attachments?.map((attachment) => attachment.id) ?? [],
          web_research: webResearch,
          request_id: requestId,
          model_id: modelMode === 'auto' ? null : modelMode,
          mode: modelMode === 'auto' ? 'goldmine' : 'single',
          experience_mode: get().experienceMode,
        }),
      });
      const result = await readEventStream(response as Response, (event) => {
        if (get().currentChatId !== chatId || pendingRequests.get(chatId) !== requestId) return;
        if (event.type === 'delta' && typeof event.text === 'string') {
          const streamId = `stream:${requestId}`;
          set((state) => {
            const existing = state.messages.find((message) => message.id === streamId);
            if (existing) return { messages: state.messages.map((message) => message.id === streamId ? { ...message, content: message.content + event.text } : message) };
            return { messages: [...state.messages, { id: streamId, chat_id: chatId!, role: 'assistant', content: event.text, created_at: new Date().toISOString() }] };
          });
        } else if (event.type === 'stage') set({ streamStatus: event.message || 'Thinking…' });
        else if (event.type === 'provider') set({ streamStatus: event.status === 'retrying' ? 'Checking another perspective…' : 'Making the best decision…' });
      });

      // Build assistant message from Goldmine result
      const assistantMsg: ChatMessage = {
        id: result.message_id || crypto.randomUUID(),
        chat_id: chatId,
        role: 'assistant',
        content: result.selected_response?.content || result.content || '',
        created_at: new Date().toISOString(),
        model_id: result.selected_response?.model_id,
        provider: result.selected_response?.provider,
        goldmine_score: result.goldmine_score,
        evaluation_signals: result.selected_response?.evaluation_signals,
        selection_explanation: result.selection_explanation,
        all_responses: result.all_responses,
        web_verified: result.web_verified,
        response_type: result.selected_response?.response_type,
        provider_failures: result.provider_failures,
        sources: result.sources,
      };

      if (get().currentChatId === chatId && pendingRequests.get(chatId) === requestId) {
        set((s) => ({ messages: [...s.messages.filter((message) => message.id !== `stream:${requestId}`), assistantMsg], isGenerating: false, streamStatus: '' }));
      }

      // Update chat title if it's the first message
      if (state.messages.length === 0) {
        get().renameChat(chatId, content.slice(0, 60));
      }
      return { chatId, success: true };
    } catch (e: any) {
      console.error('Failed to send message:', e);
      if (get().currentChatId === chatId && pendingRequests.get(chatId) === requestId) {
        const streamId = `stream:${requestId}`;
        set((s) => {
          const streamedAnswer = s.messages.find((message) => message.id === streamId);
          // The provider may have already delivered a valid answer before a
          // later persistence/network step fails. Keep that answer visible.
          if (streamedAnswer?.content.trim()) {
            return {
              messages: s.messages.map((message) => message.id === streamId
                ? { ...message, id: `local:${requestId}` }
                : message),
              isGenerating: false,
              streamStatus: '',
            };
          }
          if (e?.name === 'AbortError') return { isGenerating: false, streamStatus: '' };
          return {
            messages: [...s.messages, {
              id: crypto.randomUUID(), chat_id: chatId!, role: 'assistant',
              content: '⚠️ Goldmine could not reach an available model right now. Please try again in a moment.',
              created_at: new Date().toISOString(),
            }],
            isGenerating: false,
            streamStatus: '',
          };
        });
      }
      return { chatId: chatId || null, success: false };
    } finally {
      if (pendingRequests.get(chatId) === requestId) {
        pendingRequests.delete(chatId);
        activeControllers.delete(chatId);
        if (get().currentChatId === chatId) set({ isGenerating: false, streamStatus: '' });
      }
    }
  },

  cancelGeneration: () => {
    const currentChatId = get().currentChatId;
    if (currentChatId) activeControllers.get(currentChatId)?.abort();
  },

  setModelMode: (mode: string) => set({ modelMode: mode }),
  setExperienceMode: (mode: ExperienceMode) => set({ experienceMode: mode }),
  
  clearCurrentChat: () => set({ currentChatId: null, messages: [] }),
}));
