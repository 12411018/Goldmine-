import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Bot, Send, User, ChevronDown, Check, Paperclip, Globe2, X, FileText, Image as ImageIcon, LoaderCircle, Square, MessageCircle, BookOpen, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { 
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger 
} from '@/components/ui/dropdown-menu';
import { useChatStore } from '@/stores/chatStore';
import type { ChatMessage } from '@/stores/chatStore';
import type { AttachmentData } from '@/stores/chatStore';
import { apiClient, uploadFile } from '@/lib/api';
import { supabase } from '@/lib/supabase';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { toast } from 'sonner';
import GoldmineLogo from '@/components/brand/GoldmineLogo';

interface AvailableModel {
  id: string;
  display_name: string;
  provider: string;
  supports_vision: boolean;
}

function MessageItem({ msg, models }: { msg: ChatMessage; models: AvailableModel[] }) {
  const isUser = msg.role === 'user';
  const answerModel = msg.model_id
    ? models.find((model) => model.id === msg.model_id)?.display_name
      || msg.model_id.split('/').pop()?.replace(/:free$/, '').replace(/[-_]/g, ' ')
    : undefined;
  
  return (
    <div className={`flex gap-4 ${isUser ? 'flex-row-reverse' : ''} w-full`}>
      <Avatar className="w-8 h-8 shrink-0 mt-1">
        {isUser ? (
          <AvatarFallback className="bg-primary/20"><User className="w-4 h-4" /></AvatarFallback>
        ) : (
          <AvatarFallback className="bg-primary/10 text-primary"><Bot className="w-4 h-4" /></AvatarFallback>
        )}
      </Avatar>
      
      <div className={`flex flex-col gap-2 max-w-[85%] ${isUser ? 'items-end' : 'items-start'}`}>
        <div className={`px-4 py-3 rounded-2xl ${
          isUser 
            ? 'border border-primary/35 bg-[linear-gradient(135deg,hsl(var(--card)),hsl(var(--secondary)))] text-foreground shadow-[0_8px_24px_rgba(212,155,26,0.10)] rounded-tr-sm' 
            : 'bg-muted/50 border rounded-tl-sm'
        }`}>
          <div className="prose prose-sm dark:prose-invert max-w-none">
            {msg.content ? <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown> : (
              <span className="flex items-center gap-2 text-muted-foreground animate-pulse">
                Thinking <Bot className="w-4 h-4 animate-bounce" />
              </span>
            )}
          </div>
        </div>

        {/* Keep collaboration details reassuring rather than exposing provider internals. */}
        {!isUser && msg.content && (
          <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground mt-1">
            {msg.response_type === 'synthesis' && <span className="rounded-full border border-primary/30 bg-primary/10 px-2 py-0.5 text-primary">Goldmine team answer</span>}
            {answerModel && <span>Answered by <strong className="font-medium text-foreground/80">{answerModel}</strong></span>}
          </div>
        )}
        {isUser && msg.attachments?.length ? <div className="flex flex-wrap justify-end gap-2">{msg.attachments.map((attachment) => <span key={attachment.id} className="flex items-center gap-1.5 rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs">{attachment.mime_type.startsWith('image/') ? <ImageIcon className="h-3.5 w-3.5 text-primary" /> : <FileText className="h-3.5 w-3.5" />}{attachment.file_name}</span>)}</div> : null}
        {!isUser && msg.sources?.length ? <div className="w-full rounded-xl border border-border/70 bg-card/50 p-3"><p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Research sources</p><ul className="space-y-1.5">{msg.sources.map((source) => <li key={source.url}><a href={source.url} target="_blank" rel="noopener noreferrer" className="text-xs text-primary underline decoration-primary/30 underline-offset-2 hover:decoration-primary">{source.title} <span className="text-muted-foreground">· {source.domain}</span></a></li>)}</ul></div> : null}
      </div>
    </div>
  );
}

export default function ChatPage() {
  const { chatId } = useParams();
  const navigate = useNavigate();
  const [input, setInput] = useState('');
  const [availableModels, setAvailableModels] = useState<AvailableModel[]>([]);
  const [modelsLoading, setModelsLoading] = useState(true);
  const [modelsFailedToLoad, setModelsFailedToLoad] = useState(false);
  const [webResearch, setWebResearch] = useState(false);
  const [webResearchConfigured, setWebResearchConfigured] = useState(false);
  const [attachments, setAttachments] = useState<AttachmentData[]>([]);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  
  const { 
    messages, 
    isGenerating, 
    modelMode, 
    setModelMode, 
    experienceMode,
    setExperienceMode,
    sendMessage,
    cancelGeneration,
    streamStatus,
    selectChat,
    currentChatId
  } = useChatStore();

  useEffect(() => {
    let active = true;
    const loadModels = async () => {
      setModelsLoading(true);
      try {
        const { data } = await supabase.auth.getSession();
        const token = data.session?.access_token ?? '';
        const models = await apiClient('/api/models', { token });
        if (active) setAvailableModels(models);
      } catch (error) {
        console.error('Could not load available models:', error);
        if (active) {
          setAvailableModels([]);
          setModelsFailedToLoad(true);
        }
      } finally {
        if (active) setModelsLoading(false);
      }
    };
    void loadModels();
    return () => { active = false; };
  }, []);

  useEffect(() => {
    let active = true;
    void apiClient('/api/health').then((health) => {
      if (active) setWebResearchConfigured(health.services?.web_research === 'configured');
    }).catch(() => { if (active) setWebResearchConfigured(false); });
    return () => { active = false; };
  }, []);

  // Sync when route chatId changes
  useEffect(() => {
    if (chatId) {
      if (chatId !== currentChatId) {
        selectChat(chatId);
      }
    }
  }, [chatId, currentChatId, selectChat]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isGenerating]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if ((!input.trim() && !attachments.length) || isGenerating) return;
    
    const content = input.trim() || 'Please analyze the attached image or document and answer based on its contents.';
    setInput('');
    const result = await sendMessage(content, attachments, webResearch || (experienceMode === 'research' && webResearchConfigured));
    if (result.success) setAttachments([]);
    if (!result.success) {
      setInput(content);
      toast.error(result.chatId
        ? 'Goldmine could not generate a response. Your message is still here—please retry.'
        : 'Goldmine could not create a chat because the backend is unavailable. Please retry when it reconnects.');
    }
    if (result.chatId && result.chatId !== chatId && useChatStore.getState().currentChatId === result.chatId) {
      navigate(`/app/c/${result.chatId}`, { replace: true });
    }
  };

  const handleFiles = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(event.target.files ?? []);
    event.target.value = '';
    if (!selected.length) return;
    if (attachments.length + selected.length > 8) {
      toast.error('You can attach up to 8 files per message');
      return;
    }
    const currentImages = attachments.filter((item) => item.mime_type.startsWith('image/'));
    const selectedImages = selected.filter((file) => file.type.startsWith('image/'));
    if (currentImages.length + selectedImages.length > 4) {
      toast.error('You can attach up to 4 images per message');
      return;
    }
    const totalImageBytes = [...currentImages.map((item) => item.size_bytes), ...selectedImages.map((file) => file.size)]
      .reduce((total, size) => total + size, 0);
    if (totalImageBytes > 16 * 1024 * 1024) {
      toast.error('Combined image size must be 16 MB or less');
      return;
    }
    setUploading(true);
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token ?? '';
      let temporaryUpload = false;
      for (const file of selected) {
        setUploadProgress(0);
        const uploaded = await uploadFile<AttachmentData>('/api/attachments', file, token, setUploadProgress);
        temporaryUpload ||= Boolean(uploaded.temporary);
        setAttachments((current) => [...current, uploaded]);
      }
      toast.success(temporaryUpload ? 'File ready; upload is temporary until the database reconnects' : 'File ready to attach');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Document upload failed');
    } finally {
      setUploading(false);
      setUploadProgress(null);
    }
  };

  const removeAttachment = async (attachment: AttachmentData) => {
    try {
      const { data } = await supabase.auth.getSession();
      await apiClient(`/api/attachments/${attachment.id}`, { method: 'DELETE', token: data.session?.access_token ?? '' });
      setAttachments((current) => current.filter((item) => item.id !== attachment.id));
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Could not remove attachment');
    }
  };

  return (
    <div className="chat-workspace flex flex-col h-full">
      {/* Top Header */}
      <header className="h-14 border-b flex items-center px-4 justify-between bg-background/95 backdrop-blur z-10">
        <div className="flex items-center gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm" className="gap-2 font-semibold">
                {modelMode === 'auto'
                  ? 'Goldmine Smart'
                  : availableModels.find((model) => model.id === modelMode)?.display_name ?? 'Unavailable model'}
                <ChevronDown className="w-4 h-4 text-muted-foreground" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start">
              <DropdownMenuItem onClick={() => setModelMode('auto')} className="gap-2 justify-between">
                <span className="font-medium text-primary">Goldmine Smart</span>
                {modelMode === 'auto' && <Check className="w-4 h-4" />}
              </DropdownMenuItem>
              {modelsLoading ? (
                <div className="px-2 py-2 text-xs text-muted-foreground">Loading configured models…</div>
              ) : availableModels.length ? (
                availableModels.map((model) => (
                  <DropdownMenuItem key={model.id} onClick={() => setModelMode(model.id)} className="gap-2 justify-between">
                    <span>{model.display_name} <span className="text-muted-foreground">· {model.provider}</span></span>
                    {modelMode === model.id && <Check className="w-4 h-4" />}
                  </DropdownMenuItem>
                ))
              ) : (
                <div className="max-w-64 px-2 py-2 text-xs text-muted-foreground">{modelsFailedToLoad ? 'Could not load models. Check the API connection.' : 'Add OPENROUTER_API_KEY to the backend .env to enable free models. Free endpoints have daily limits.'}</div>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </header>

      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto p-4" ref={scrollRef}>
        <div className="max-w-3xl mx-auto space-y-6 pb-6">
          {messages.length === 0 && !isGenerating ? (
            /* Empty State */
            <div className="h-[58vh] flex flex-col items-center justify-center text-center space-y-4">
              <div className="brand-orb chat-brand-orb flex items-center justify-center rounded-xl">
                <GoldmineLogo size="medium" className="h-full w-full rounded-[0.6rem]" />
              </div>
              <div className="space-y-2">
                <p className="text-xs font-medium uppercase tracking-[0.22em] text-primary/90">Your research workspace</p>
                <h2 className="text-3xl font-semibold tracking-tight">What are we thinking through?</h2>
              </div>
              <p className="text-muted-foreground max-w-md text-sm leading-6">
                Goldmine knows when to answer directly and when to bring its best AI minds together.
              </p>
              <div className="mt-3 flex max-w-2xl flex-wrap justify-center gap-2">
                {['Compare approaches to a problem', 'Explain a complex idea simply', 'Help me review this code'].map((suggestion) => (
                  <button key={suggestion} type="button" onClick={() => setInput(suggestion)} className="suggestion-chip rounded-full border border-border/80 bg-card/70 px-4 py-2 text-xs text-muted-foreground transition hover:border-primary/50 hover:text-foreground">
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            /* Message List */
            <div className="space-y-6">
              {messages.map((msg, idx) => (
                <MessageItem key={msg.id || idx} msg={msg} models={availableModels} />
              ))}

              {/* Live Thinking Indicator */}
              {isGenerating && (
                <div className="flex gap-4 w-full animate-in fade-in-50 duration-300">
                  <Avatar className="w-8 h-8 shrink-0 mt-1 border border-primary/20 shadow-sm">
                    <AvatarFallback className="bg-primary/10 text-primary">
                      <Bot className="w-4 h-4 animate-spin text-primary" />
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex flex-col gap-2 max-w-[85%] items-start">
                    <div className="px-4 py-3 rounded-2xl bg-muted/60 border border-primary/20 rounded-tl-sm shadow-sm flex items-center gap-3">
                      <div className="flex space-x-1.5 items-center">
                        <div className="w-2 h-2 bg-primary rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                        <div className="w-2 h-2 bg-primary rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                        <div className="w-2 h-2 bg-primary rounded-full animate-bounce"></div>
                      </div>
                      <span className="text-sm text-foreground/80 font-medium">
                        {streamStatus || 'Preparing your response…'}
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Input Area */}
      <div className="p-4 bg-background">
        <div className="composer-shell max-w-3xl mx-auto relative">
          {attachments.length > 0 && <div className="mb-2 flex flex-wrap gap-2">{attachments.map((attachment) => <span key={attachment.id} className="flex items-center gap-2 rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs">{attachment.mime_type.startsWith('image/') ? <ImageIcon className="h-3.5 w-3.5 text-primary" /> : <FileText className="h-3.5 w-3.5 text-primary" />}{attachment.file_name}<button type="button" aria-label={`Remove ${attachment.file_name}`} onClick={() => void removeAttachment(attachment)} className="rounded text-muted-foreground hover:text-destructive"><X className="h-3.5 w-3.5" /></button></span>)}</div>}
          {attachments.some((attachment) => attachment.mime_type.startsWith('image/')) && <p className="mb-2 px-1 text-[11px] text-muted-foreground">Images are analyzed by Goldmine’s free vision model. Avoid confidential or personal images.</p>}
          {uploading && <div className="mb-2 flex items-center gap-2 text-xs text-muted-foreground"><LoaderCircle className="h-3.5 w-3.5 animate-spin" />Uploading files · {uploadProgress ?? 0}%</div>}
          <form onSubmit={handleSubmit} className="relative">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask anything..."
              className="min-h-[60px] max-h-[200px] pl-24 pr-28 resize-none rounded-xl bg-muted/50 border-muted-foreground/20 focus-visible:ring-primary/50 text-base py-4"
              rows={1}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(e);
                }
              }}
            />
            
            <div className="absolute left-2 bottom-2 flex items-center gap-1">
              <input ref={fileInput} type="file" accept=".pdf,.docx,.txt,.md,.png,.jpg,.jpeg,.webp,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown,image/png,image/jpeg,image/webp" multiple className="hidden" onChange={handleFiles} />
              <Button type="button" variant="ghost" size="icon" title="Attach PDF, DOCX, TXT, Markdown, PNG, JPG, or WebP" aria-label="Attach a file or image" disabled={uploading || isGenerating} onClick={() => fileInput.current?.click()}><Paperclip className="h-4 w-4" /></Button>
              <Button type="button" variant={webResearch ? 'secondary' : 'ghost'} size="icon" title={webResearchConfigured ? 'Toggle web research' : 'Web research needs SEARCH_API_KEY'} aria-label="Toggle web research" aria-pressed={webResearch} disabled={isGenerating} onClick={() => {
                if (!webResearchConfigured) { toast.info('Web research is ready to connect. Add SEARCH_API_KEY on the backend to enable cited live results.'); return; }
                setWebResearch((value) => !value);
              }}><Globe2 className={`h-4 w-4 ${webResearch ? 'text-primary' : ''}`} /></Button>
            </div>
            <div className="absolute right-2 bottom-2 flex items-center gap-1">
              {isGenerating ? <Button type="button" variant="destructive" size="icon" aria-label="Stop response" title="Stop response" onClick={cancelGeneration}><Square className="h-3.5 w-3.5" /></Button> : (
              <Button 
                type="submit" 
                size="icon" 
                disabled={(!input.trim() && !attachments.length) || isGenerating || uploading}
                className="bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm"
              >
                <Send className="w-4 h-4" />
              </Button>
              )}
            </div>
          </form>
          <div className="mt-2 flex flex-wrap items-center gap-1.5 px-1">
            {([
              ['normal', 'Chat', MessageCircle, 'Direct answers, with teamwork when it helps'],
              ['study', 'Study', BookOpen, 'Clear explanations and learning support'],
              ['research', 'Research', Search, 'Uses team reasoning and cited web research when connected'],
            ] as const).map(([mode, label, Icon, title]) => <button key={mode} type="button" title={title} onClick={() => setExperienceMode(mode)} disabled={isGenerating} className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] transition ${experienceMode === mode ? 'border-primary/55 bg-primary/15 text-primary' : 'border-border bg-card/50 text-muted-foreground hover:border-primary/35 hover:text-foreground'}`}><Icon className="h-3 w-3" />{label}</button>)}
            <span className="ml-1 text-[11px] text-muted-foreground">Goldmine chooses the right number of brains for each task.</span>
          </div>
          {webResearch && <p className="mt-2 text-center text-[11px] text-primary">Web research is enabled for this message. Results will be cited when used.</p>}
          <div className="text-center mt-2">
            <span className="text-[11px] text-muted-foreground">
              Goldmine AI can make mistakes. Consider verifying important information.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
