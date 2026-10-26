import { useCallback, useEffect, useState } from 'react';
import { Settings2, Sparkles, UserRound } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { apiClient } from '@/lib/api';
import { supabase } from '@/lib/supabase';
import { toast } from 'sonner';

type Tone = 'friendly' | 'professional' | 'balanced';
type Preferences = { display_name: string; tone: Tone };

async function getToken() {
  const { data } = await supabase.auth.getSession();
  if (!data.session?.access_token) throw new Error('Your session expired. Please sign in again.');
  return data.session.access_token;
}

export default function SettingsPage() {
  const [displayName, setDisplayName] = useState('');
  const [tone, setTone] = useState<Tone>('friendly');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const loadPreferences = useCallback(async () => {
    let storageKey = '';
    let cached: Preferences | null = null;
    try {
      const { data } = await supabase.auth.getSession();
      if (!data.session?.access_token) throw new Error('Your session expired. Please sign in again.');
      storageKey = `goldmine:preferences:${data.session.user.id}`;
      try {
        const saved = localStorage.getItem(storageKey);
        if (saved) {
          const value = JSON.parse(saved) as Preferences;
          if (typeof value.display_name === 'string' && ['friendly', 'professional', 'balanced'].includes(value.tone)) {
            cached = value;
            setDisplayName(value.display_name);
            setTone(value.tone);
          }
        }
      } catch {
        localStorage.removeItem(storageKey);
      }
      const preferences = await apiClient('/api/preferences', { token: await getToken() });
      if (preferences.temporary && cached) {
        await apiClient('/api/preferences', {
          method: 'PATCH', token: await getToken(),
          body: JSON.stringify(cached),
        });
        return;
      }
      setDisplayName(preferences.display_name || '');
      setTone(preferences.tone || 'friendly');
      localStorage.setItem(storageKey, JSON.stringify({ display_name: preferences.display_name || '', tone: preferences.tone || 'friendly' }));
    } catch (error) {
      if (!cached) toast.error(error instanceof Error ? error.message : 'Could not load settings');
    } finally {
      setLoading(false);
    }
  }, []);

  // oxlint-disable-next-line react/set-state-in-effect
  useEffect(() => { void loadPreferences(); }, [loadPreferences]);

  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!displayName.trim()) return;
    setSaving(true);
    try {
      const saved = await apiClient('/api/preferences', {
        method: 'PATCH', token: await getToken(),
        body: JSON.stringify({ display_name: displayName.trim(), tone }),
      });
      const { data } = await supabase.auth.getSession();
      if (data.session?.user.id) {
        localStorage.setItem(`goldmine:preferences:${data.session.user.id}`, JSON.stringify({ display_name: displayName.trim(), tone }));
      }
      toast.success(saved.temporary
        ? 'Personalization saved for this session; it will sync when the database reconnects'
        : 'Personalization saved to your Goldmine memory');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Could not save settings');
    } finally {
      setSaving(false);
    }
  };

  return <section className="flex-1 overflow-y-auto px-5 py-10 sm:px-8">
    <div className="mx-auto max-w-2xl">
      <div className="mb-8 flex items-center gap-4">
        <div className="brand-orb flex h-12 w-12 items-center justify-center rounded-2xl"><Settings2 className="h-6 w-6 text-primary" /></div>
        <div><p className="text-xs font-medium uppercase tracking-[0.2em] text-primary">Your Goldmine</p><h1 className="text-2xl font-semibold">Settings & personalization</h1></div>
      </div>
      <p className="mb-6 max-w-xl text-sm leading-6 text-muted-foreground">Tell Goldmine how to address you and how you like it to communicate. This preference is stored in your memory and can be changed any time.</p>
      <form onSubmit={save} className="space-y-7 rounded-2xl border border-border/80 bg-card/75 p-5 shadow-xl shadow-black/10">
        <div className="space-y-2"><label htmlFor="display-name" className="flex items-center gap-2 text-sm font-medium"><UserRound className="h-4 w-4 text-primary" />What should Goldmine call you?</label><Input id="display-name" value={displayName} disabled={loading} onChange={(event) => setDisplayName(event.target.value)} maxLength={80} placeholder="Your name" className="bg-background/70" /></div>
        <fieldset disabled={loading || saving}><legend className="mb-3 flex items-center gap-2 text-sm font-medium"><Sparkles className="h-4 w-4 text-primary" />Assistant tone</legend><div className="grid gap-2 sm:grid-cols-3">{([
          ['friendly', 'Friendly', 'Warm, encouraging, and natural'],
          ['professional', 'Professional', 'Focused, precise, and structured'],
          ['balanced', 'Balanced', 'Clear, helpful, and adaptable'],
        ] as const).map(([value, label, description]) => <button key={value} type="button" onClick={() => setTone(value)} className={`rounded-xl border p-3 text-left transition ${tone === value ? 'border-primary/60 bg-primary/10' : 'border-border bg-background/45 hover:border-primary/35'}`}><span className="block text-sm font-medium">{label}</span><span className="mt-1 block text-xs leading-5 text-muted-foreground">{description}</span></button>)}</div></fieldset>
        <div className="flex justify-end"><Button type="submit" disabled={loading || saving || !displayName.trim()}>{saving ? 'Saving…' : 'Save personalization'}</Button></div>
      </form>
    </div>
  </section>;
}
