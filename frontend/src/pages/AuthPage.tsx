import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { motion } from 'motion/react';
import { ArrowLeft, ArrowRight, Check, KeyRound, LoaderCircle, LockKeyhole, Mail, ShieldCheck, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';
import { useAuthStore } from '@/stores/authStore';
import { supabase } from '@/lib/supabase';
import GoldmineLogo from '@/components/brand/GoldmineLogo';

type AuthView = 'login' | 'signup' | 'forgot' | 'reset';

function GoogleMark() {
  return (
    <svg aria-hidden="true" viewBox="0 0 48 48" className="h-[18px] w-[18px]">
      <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.73 7.18l7.64 5.93c4.46-4.12 7.13-10.2 7.13-17.58Z" />
      <path fill="#34A853" d="M24 48c6.47 0 11.9-2.13 15.85-5.87l-7.64-5.93c-2.13 1.43-4.85 2.3-8.21 2.3-6.26 0-11.57-4.22-13.46-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48Z" />
      <path fill="#FBBC05" d="M10.54 28.59a14.4 14.4 0 0 1 0-9.18l-7.98-6.19a23.9 23.9 0 0 0 0 21.56l7.98-6.19Z" />
      <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5Z" />
    </svg>
  );
}

export default function AuthPage() {
  const [view, setView] = useState<AuthView>(() => new URLSearchParams(window.location.search).get('mode') === 'reset' ? 'reset' : 'login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [resetSent, setResetSent] = useState(false);
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { signIn, signUp, signInWithGoogle, resetPassword, updatePassword, loading, session } = useAuthStore();

  useEffect(() => {
    if (searchParams.get('mode') === 'reset') setView('reset');
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event) => {
      if (event === 'PASSWORD_RECOVERY') setView('reset');
    });
    return () => subscription.unsubscribe();
  }, [searchParams]);

  useEffect(() => {
    if (session && view !== 'reset') navigate('/app', { replace: true });
  }, [session, view, navigate]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (view === 'forgot') {
      const { error } = await resetPassword(email);
      if (error) toast.error(error);
      else setResetSent(true);
      return;
    }
    if (view === 'reset') {
      if (password !== confirmPassword) { toast.error('Your passwords do not match'); return; }
      const { error } = await updatePassword(password);
      if (error) toast.error(error);
      else { toast.success('Password updated. You’re all set.'); navigate('/app', { replace: true }); }
      return;
    }
    if (view === 'signup') {
      const { error } = await signUp(email, password);
      if (error) toast.error(error);
      else { toast.success('Account created. Check your email to confirm, then sign in.'); setView('login'); }
      return;
    }
    const { error } = await signIn(email, password);
    if (error) toast.error(error);
    else { toast.success('Welcome back!'); navigate('/app'); }
  };

  const handleGoogleSignIn = async () => {
    const { error } = await signInWithGoogle();
    if (error) toast.error(error);
  };

  const isRecovery = view === 'forgot' || view === 'reset';
  const title = view === 'signup' ? 'Create your account' : view === 'forgot' ? 'Reset your password' : view === 'reset' ? 'Choose a new password' : 'Welcome back';
  const description = view === 'signup'
    ? 'Start a more thoughtful conversation with AI.'
    : view === 'forgot'
      ? 'We’ll send a secure reset link to your email.'
      : view === 'reset'
        ? 'Choose a new password for your Goldmine account.'
        : 'Sign in to pick up where your ideas left off.';

  return (
    <main className="auth-page">
      <div className="auth-ambient auth-ambient-one" />
      <div className="auth-ambient auth-ambient-two" />
      <Link to="/" className="auth-back"><ArrowLeft size={16} /> <span>Back to home</span></Link>

      <div className="auth-layout">
        <motion.section className="auth-story" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.65, ease: [0.22, 1, 0.36, 1] }}>
          <Link to="/" className="auth-story-brand"><GoldmineLogo size="medium" /><span>Goldmine <i>AI</i></span></Link>
          <div className="auth-story-copy">
            <span className="auth-story-kicker"><Sparkles size={14} /> A clearer way to use AI</span>
            <h1>Better thinking<br />starts <span>together.</span></h1>
            <p>Ask a quick question, explore a topic, or let Goldmine bring multiple AI perspectives into one considered answer.</p>
            <div className="auth-story-points">
              <span><Check size={15} /> One thoughtful workspace</span>
              <span><Check size={15} /> Chat, study, and research modes</span>
            </div>
          </div>
          <div className="auth-story-foot"><ShieldCheck size={15} /> Your account, your conversations, your control.</div>
        </motion.section>

        <motion.section className="auth-card-wrap" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, delay: 0.08, ease: [0.22, 1, 0.36, 1] }}>
          <div className="auth-card">
            <div className="auth-card-heading">
              <div className="auth-card-mark"><GoldmineLogo size="small" /></div>
              <h2>{title}</h2>
              <p>{description}</p>
            </div>

            {view === 'forgot' && resetSent ? (
              <div className="auth-success-panel" role="status">
                <span><Mail size={18} /></span>
                <b>Check your inbox</b>
                <p>If an account exists for <strong>{email}</strong>, a password reset link is on its way.</p>
                <button type="button" className="auth-text-button" onClick={() => { setResetSent(false); setView('login'); }}>Back to sign in</button>
              </div>
            ) : (
              <>
                {!isRecovery && (
                  <>
                    <Button type="button" variant="outline" className="auth-google-button" disabled={loading} onClick={() => void handleGoogleSignIn()}>
                      {loading ? <LoaderCircle size={17} className="animate-spin" /> : <GoogleMark />}
                      Continue with Google
                    </Button>
                    <div className="auth-divider"><span>or continue with email</span></div>
                  </>
                )}

                <form onSubmit={handleSubmit} className="auth-form">
                  {view !== 'reset' && <label className="auth-field"><span>Email address</span><span className="auth-input-wrap"><Mail size={16} /><Input type="email" placeholder="you@example.com" value={email} onChange={(event) => setEmail(event.target.value)} required autoComplete="email" /></span></label>}
                  {view !== 'forgot' && <label className="auth-field"><span>{view === 'reset' ? 'New password' : 'Password'}</span><span className="auth-input-wrap"><LockKeyhole size={16} /><Input type="password" placeholder={view === 'reset' ? 'At least 6 characters' : 'At least 6 characters'} value={password} onChange={(event) => setPassword(event.target.value)} required minLength={6} autoComplete={view === 'login' ? 'current-password' : 'new-password'} /></span></label>}
                  {view === 'reset' && <label className="auth-field"><span>Confirm new password</span><span className="auth-input-wrap"><KeyRound size={16} /><Input type="password" placeholder="Enter your new password again" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} required minLength={6} autoComplete="new-password" /></span></label>}
                  {view === 'login' && <div className="auth-forgot-row"><button type="button" className="auth-text-button" onClick={() => setView('forgot')}>Forgot password?</button></div>}
                  <Button type="submit" className="auth-submit" disabled={loading}>
                    {loading ? <><LoaderCircle size={16} className="animate-spin" /> Please wait…</> : <>{view === 'signup' ? 'Create account' : view === 'forgot' ? 'Send reset link' : view === 'reset' ? 'Update password' : 'Sign in'} <ArrowRight size={16} /></>}
                  </Button>
                </form>

                <div className="auth-switch-row">
                  {view === 'forgot' || view === 'reset' ? (
                    <button type="button" className="auth-text-button" onClick={() => { setView('login'); setResetSent(false); }}>Back to sign in</button>
                  ) : (
                    <><span>{view === 'signup' ? 'Already have an account?' : 'New to Goldmine?'}</span><button type="button" className="auth-text-button" onClick={() => setView(view === 'signup' ? 'login' : 'signup')}>{view === 'signup' ? 'Sign in' : 'Create an account'}</button></>
                  )}
                </div>
              </>
            )}
          </div>
          <p className="auth-privacy-note"><ShieldCheck size={13} /> Secure sign-in powered by Supabase Auth</p>
        </motion.section>
      </div>
    </main>
  );
}
