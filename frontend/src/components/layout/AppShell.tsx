import { useEffect } from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import Sidebar from './Sidebar';

export default function AppShell() {
  const { session, initialized } = useAuthStore();
  const navigate = useNavigate();

  useEffect(() => {
    if (initialized && !session) {
      navigate('/auth');
    }
  }, [session, initialized, navigate]);

  if (!initialized || !session) return null;

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar />
      <main className="flex-1 relative flex flex-col min-w-0">
        <Outlet />
      </main>
    </div>
  );
}
