import { useCallback, useEffect, useState } from 'react';
import { BrainCircuit, LoaderCircle, Pencil, Plus, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { apiClient } from '@/lib/api';
import { supabase } from '@/lib/supabase';
import { toast } from 'sonner';

interface Memory {
  id: string;
  content: string;
  category: string;
  importance: number;
  enabled: boolean;
  created_at: string;
  temporary?: boolean;
}

async function tokenOrThrow() {
  const { data } = await supabase.auth.getSession();
  if (!data.session?.access_token) throw new Error('Your session expired. Please sign in again.');
  return data.session.access_token;
}

export default function MemoryPage() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [databaseReady, setDatabaseReady] = useState<boolean | null>(null);

  const loadMemories = useCallback(async () => {
    try {
      const health = await apiClient('/api/health');
      setDatabaseReady(Boolean(health.services?.database?.ready));
      const token = await tokenOrThrow();
      const rows = await apiClient('/api/memory', { token });
      setMemories(rows);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Could not load memories');
    } finally {
      setLoading(false);
    }
  }, []);

  // Load remote, user-scoped data once the page mounts.
  // oxlint-disable-next-line react/set-state-in-effect
  useEffect(() => { void loadMemories(); }, [loadMemories]);

  const addMemory = async (event: React.FormEvent) => {
    event.preventDefault();
    const value = content.trim();
    if (!value) return;
    setSaving(true);
    try {
      const token = await tokenOrThrow();
      const memory = await apiClient('/api/memory', {
        method: 'POST', token,
        body: JSON.stringify({ content: value, category: 'general', importance: 5 }),
      });
      setMemories((current) => [memory, ...current]);
      setContent('');
      toast.success(memory.temporary ? 'Memory saved temporarily until Supabase reconnects' : 'Memory saved');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Could not save memory');
    } finally {
      setSaving(false);
    }
  };

  const updateMemory = async (memory: Memory, changes: Partial<Memory>) => {
    try {
      const token = await tokenOrThrow();
      const saved = await apiClient(`/api/memory/${memory.id}`, {
        method: 'PATCH', token,
        body: JSON.stringify(changes),
      });
      setMemories((current) => current.map((item) => item.id === memory.id ? { ...item, ...changes } : item));
      toast.success(saved.temporary ? 'Memory updated temporarily until Supabase reconnects' : 'Memory updated');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Could not update memory');
    }
  };

  const removeMemory = async (memory: Memory) => {
    if (!window.confirm('Delete this saved memory?')) return;
    try {
      const token = await tokenOrThrow();
      const result = await apiClient(`/api/memory/${memory.id}`, { method: 'DELETE', token });
      setMemories((current) => current.filter((item) => item.id !== memory.id));
      toast.success(result.temporary ? 'Temporary memory deleted' : 'Memory deleted');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Could not delete memory');
    }
  };

  return (
    <section className="memory-page flex-1 overflow-y-auto px-5 py-10 sm:px-8">
      <div className="mx-auto max-w-3xl">
        <div className="mb-8 flex items-center gap-4">
          <div className="brand-orb flex h-12 w-12 items-center justify-center rounded-2xl"><BrainCircuit className="h-6 w-6 text-primary" /></div>
          <div><p className="text-xs font-medium uppercase tracking-[0.2em] text-primary">Personal context</p><h1 className="text-2xl font-semibold">Memory</h1></div>
        </div>
        <p className="mb-6 max-w-2xl text-sm leading-6 text-muted-foreground">These notes may be included when Goldmine prepares a response. You control what is saved and can disable or remove any note.</p>
        {databaseReady === false && <div role="status" className="mb-6 rounded-xl border border-primary/30 bg-primary/5 px-4 py-3 text-sm text-muted-foreground">Supabase Postgres is offline. New memories are temporary for this backend session; saved memories will reappear when the project reconnects.</div>}

        <form onSubmit={addMemory} className="mb-8 space-y-3 rounded-2xl border border-border/80 bg-card/75 p-4 shadow-xl shadow-black/10">
          <label htmlFor="memory-content" className="text-sm font-medium">Add a memory</label>
          <Textarea id="memory-content" value={content} onChange={(event) => setContent(event.target.value)} maxLength={2000} placeholder="For example: I prefer concise explanations with practical examples." className="min-h-24 resize-y bg-background/70" />
          <div className="flex items-center justify-between gap-3">
            <span className="text-xs text-muted-foreground">Only save information you want used as context.</span>
            <Button type="submit" disabled={saving || !content.trim()} className="gap-2"><Plus className="h-4 w-4" />{saving ? 'Saving…' : 'Save memory'}</Button>
          </div>
        </form>

        <div className="space-y-3">
          {loading ? <div className="flex items-center gap-2 py-8 text-sm text-muted-foreground"><LoaderCircle className="h-4 w-4 animate-spin" />Loading your memories…</div>
            : memories.length === 0 ? <div className="rounded-2xl border border-dashed border-border p-8 text-center text-sm text-muted-foreground">No memories saved yet.</div>
              : memories.map((memory) => (
                <article key={memory.id} className={`rounded-2xl border border-border/80 bg-card/65 p-4 transition ${memory.enabled ? '' : 'opacity-55'}`}>
                  <p className="whitespace-pre-wrap text-sm leading-6">{memory.content}</p>
                  <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                    <span className="text-xs text-muted-foreground">{memory.category} · importance {memory.importance}</span>
                    <div className="flex items-center gap-2">
                      <label className="flex items-center gap-2 text-xs text-muted-foreground">
                        <input type="checkbox" checked={memory.enabled} onChange={(event) => void updateMemory(memory, { enabled: event.target.checked })} />
                        Include in context
                      </label>
                      <Button variant="ghost" size="icon" aria-label="Edit memory" title="Edit memory" onClick={() => {
                        const next = window.prompt('Edit memory', memory.content)?.trim();
                        if (next && next !== memory.content) void updateMemory(memory, { content: next });
                      }}><Pencil className="h-4 w-4" /></Button>
                      <Button variant="ghost" size="icon" aria-label="Delete memory" title="Delete memory" onClick={() => void removeMemory(memory)}><Trash2 className="h-4 w-4 text-destructive" /></Button>
                    </div>
                  </div>
                </article>
              ))}
        </div>
      </div>
    </section>
  );
}
