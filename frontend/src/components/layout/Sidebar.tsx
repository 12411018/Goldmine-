import { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { MessageSquare, Plus, LogOut, Pencil, Search, Trash2, BrainCircuit, Settings2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { useAuthStore } from '@/stores/authStore';
import { useChatStore } from '@/stores/chatStore';
import { apiClient } from '@/lib/api';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { toast } from 'sonner';
import GoldmineLogo from '@/components/brand/GoldmineLogo';

export default function Sidebar() {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [databaseReady, setDatabaseReady] = useState<boolean | null>(null);
  const { user, signOut } = useAuthStore();
  const { chats, loadChats, currentChatId, clearCurrentChat, renameChat, deleteChat } = useChatStore();
  const visibleChats = chats.filter((chat) => chat.title.toLowerCase().includes(search.toLowerCase()));

  useEffect(() => {
    loadChats();
    void apiClient('/api/health')
      .then((health) => setDatabaseReady(Boolean(health.services?.database?.ready)))
      .catch(() => setDatabaseReady(null));
  }, [loadChats]);

  const handleSignOut = async () => {
    await signOut();
    navigate('/');
  };

  const handleNewChat = () => {
    clearCurrentChat();
    navigate('/app');
  };

  return (
    <div className="goldmine-sidebar w-64 border-r bg-sidebar h-full flex flex-col">
      <div className="p-4 flex items-center gap-2">
        <GoldmineLogo size="small" />
        <span className="font-semibold text-lg tracking-tight">Goldmine AI</span>
      </div>

      <div className="px-3 pb-2">
        <Button onClick={handleNewChat} className="w-full justify-start gap-2 h-10" variant="default">
          <Plus className="w-4 h-4" />
          New Chat
        </Button>
      </div>

      <div className="flex-1 overflow-hidden">
        <ScrollArea className="h-full">
          <div className="p-3 space-y-4">
            <div>
              <h3 className="px-2 text-xs font-semibold text-muted-foreground tracking-wider mb-2">History</h3>
              <label className="mb-2 flex items-center gap-2 rounded-lg border border-sidebar-border bg-background/60 px-2.5">
                <Search className="h-3.5 w-3.5 text-muted-foreground" />
                <input aria-label="Search conversations" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search chats" className="h-9 min-w-0 flex-1 bg-transparent text-xs outline-none placeholder:text-muted-foreground" />
              </label>
              <div className="space-y-1">
                {visibleChats.length === 0 ? (
                  <div className="px-2 text-xs text-muted-foreground py-2">{search ? 'No matching chats.' : databaseReady === false ? 'Chat history is temporarily unavailable. Existing chats have not been deleted; reconnect Supabase to see them.' : 'No chats yet.'}</div>
                ) : (
                  visibleChats.map((chat) => (
                    <div key={chat.id} className={`group flex items-center rounded-lg ${currentChatId === chat.id ? 'bg-sidebar-accent' : 'hover:bg-sidebar-accent/70'}`}>
                      <Link to={`/app/c/${chat.id}`} className="flex h-9 min-w-0 flex-1 items-center gap-2 px-2 text-sm">
                        <MessageSquare className="h-4 w-4 shrink-0 text-muted-foreground" />
                        <span className="truncate">{chat.title}</span>
                      </Link>
                      <button aria-label={`Rename ${chat.title}`} title="Rename" className="rounded p-1.5 text-muted-foreground opacity-0 hover:text-foreground focus:opacity-100 group-hover:opacity-100" onClick={async () => {
                        const title = window.prompt('Rename conversation', chat.title)?.trim();
                        if (!title || title === chat.title) return;
                        if (await renameChat(chat.id, title)) toast.success('Conversation renamed');
                        else toast.error('Could not rename conversation');
                      }}><Pencil className="h-3.5 w-3.5" /></button>
                      <button aria-label={`Delete ${chat.title}`} title="Delete" className="mr-1 rounded p-1.5 text-muted-foreground opacity-0 hover:text-destructive focus:opacity-100 group-hover:opacity-100" onClick={async () => {
                        if (!window.confirm(`Delete “${chat.title}”? This cannot be undone.`)) return;
                        if (await deleteChat(chat.id)) {
                          toast.success('Conversation deleted');
                          if (currentChatId === chat.id) navigate('/app');
                        } else toast.error('Could not delete conversation');
                      }}><Trash2 className="h-3.5 w-3.5" /></button>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </ScrollArea>
      </div>

      <div className="p-3 border-t">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="w-full justify-start gap-2 h-12 px-2 hover:bg-muted/50">
              <Avatar className="w-6 h-6">
                <AvatarFallback className="bg-primary/10 text-primary text-xs">
                  {user?.email?.charAt(0).toUpperCase() || 'U'}
                </AvatarFallback>
              </Avatar>
              <div className="flex flex-col items-start truncate">
                <span className="text-sm font-medium leading-none truncate w-full">
                  {user?.email}
                </span>
              </div>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-56">
            <DropdownMenuLabel>My Account</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild className="gap-2">
              <Link to="/app/memory"><BrainCircuit className="h-4 w-4" />Memory</Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild className="gap-2">
              <Link to="/app/settings"><Settings2 className="h-4 w-4" />Settings</Link>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="gap-2 text-destructive focus:text-destructive" onClick={handleSignOut}>
              <LogOut className="w-4 h-4" />
              Log out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
}
