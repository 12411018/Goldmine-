import { Link } from 'react-router-dom';
import { motion, useReducedMotion } from 'motion/react';
import {
  ArrowDown,
  ArrowRight,
  BookOpen,
  Check,
  FileImage,
  Globe,
  Layers,
  MessageSquare,
  ShieldCheck,
  Sparkles,
  Zap,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import GoldmineLogo from '@/components/brand/GoldmineLogo';

const currentYear = new Date().getFullYear();

const features = [
  {
    icon: Layers,
    number: '01',
    title: 'More than one perspective',
    desc: 'Goldmine can bring multiple AI models together for complex questions, then shape their best ideas into one clear response.',
  },
  {
    icon: Globe,
    number: '02',
    title: 'Research with sources',
    desc: 'Turn on web research when a question needs current information. Explore the cited sources alongside the answer.',
  },
  {
    icon: FileImage,
    number: '03',
    title: 'Ask about your files',
    desc: 'Add an image or supported document to get an answer grounded in what you shared.',
  },
];

const riseIn = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0 },
};

export default function LandingPage() {
  const reduceMotion = useReducedMotion() ?? false;

  return (
    <div className="landing-page">
      <header className="landing-header">
        <Link to="/" className="landing-brand" aria-label="Goldmine AI home">
          <GoldmineLogo size="small" />
          <span>Goldmine<span className="landing-brand-ai"> AI</span></span>
        </Link>
        <nav className="landing-nav" aria-label="Main navigation">
          <a href="#how-it-works">How it works</a>
          <a href="#capabilities">Capabilities</a>
        </nav>
        <div className="landing-header-actions">
          <Link to="/auth" className="landing-login">Log in</Link>
          <Button asChild size="sm" className="landing-nav-cta">
            <Link to="/auth">Get started <ArrowRight size={15} /></Link>
          </Button>
        </div>
      </header>

      <main>
        <section className="landing-hero">
          <div className="landing-hero-glow landing-hero-glow-one" />
          <div className="landing-hero-glow landing-hero-glow-two" />
          <motion.div
            className="landing-hero-copy"
            initial="hidden"
            animate="visible"
            variants={{ visible: { transition: { staggerChildren: 0.12 } } }}
          >
            <motion.div variants={riseIn} transition={{ duration: 0.65, ease: [0.22, 1, 0.36, 1] }} className="landing-eyebrow">
              <span className="landing-eyebrow-dot"><Sparkles size={13} /></span>
              A clearer way to use AI
            </motion.div>
            <motion.h1 variants={riseIn} transition={{ duration: 0.75, ease: [0.22, 1, 0.36, 1] }}>
              Big questions deserve<br />
              <span>more than one mind.</span>
            </motion.h1>
            <motion.p variants={riseIn} transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }} className="landing-hero-description">
              Meet your AI thinking partner. Get a direct answer for everyday questions—or bring several models together when the question needs more.
            </motion.p>
            <motion.div variants={riseIn} transition={{ duration: 0.65, ease: [0.22, 1, 0.36, 1] }} className="landing-hero-actions">
              <Button asChild size="lg" className="landing-primary-cta">
                <Link to="/auth">Start a conversation <ArrowRight size={17} /></Link>
              </Button>
              <a className="landing-secondary-cta" href="#how-it-works">See how it works <ArrowDown size={15} /></a>
            </motion.div>
            <motion.div variants={riseIn} transition={{ duration: 0.6 }} className="landing-proof-line">
              <span><Check size={14} /> One simple workspace</span>
              <i />
              <span><Check size={14} /> Chat, study, or research</span>
            </motion.div>
          </motion.div>

          <motion.div
            className="landing-visual-wrap"
            initial={{ opacity: 0, y: 34, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.9, delay: 0.2, ease: [0.22, 1, 0.36, 1] }}
          >
            <div className="landing-visual-orbit landing-visual-orbit-a" />
            <div className="landing-visual-orbit landing-visual-orbit-b" />
            <motion.div className="landing-mini-card landing-mini-card-top" animate={{ y: reduceMotion ? 0 : [0, -7, 0] }} transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }}>
              <span className="landing-mini-icon"><Globe size={15} /></span>
              <span><b>Research mode</b><small>Sources at your fingertips</small></span>
              <span className="landing-live-dot" />
            </motion.div>
            <div className="landing-product-card">
              <div className="landing-product-head">
                <div className="landing-product-title"><GoldmineLogo size="small" /><span>Goldmine <small>AI WORKSPACE</small></span></div>
                <span className="landing-mode-pill"><Sparkles size={12} /> Smart mode</span>
              </div>
              <div className="landing-prompt-bubble">
                <span className="landing-user-dot">N</span>
                <span>How can I learn a complex topic more effectively?</span>
              </div>
              <div className="landing-thinking-row">
                <span className="landing-thinking-icon"><Layers size={15} /></span>
                <span className="landing-thinking-label">Bringing the best ideas together</span>
                <span className="landing-thinking-dots"><i /><i /><i /></span>
              </div>
              <div className="landing-answer-card">
                <div className="landing-answer-heading"><span className="landing-answer-mark"><Sparkles size={14} /></span><b>A thoughtful answer</b><span className="landing-answer-tag">SYNTHESIZED</span></div>
                <p>Start with a clear goal, break the subject into small pieces, and practice recalling what you learn. Then use feedback to focus your next study session.</p>
                <div className="landing-answer-footer"><span><BookOpen size={13} /> Study plan</span><span><ShieldCheck size={13} /> Multiple perspectives</span></div>
              </div>
              <div className="landing-composer"><MessageSquare size={15} /><span>Ask anything…</span><span className="landing-composer-send"><ArrowRight size={15} /></span></div>
            </div>
            <motion.div className="landing-mini-card landing-mini-card-bottom" animate={{ y: reduceMotion ? 0 : [0, 6, 0] }} transition={{ duration: 5.5, repeat: Infinity, ease: 'easeInOut', delay: 0.7 }}>
              <span className="landing-mini-icon landing-mini-icon-gold"><Zap size={15} /></span>
              <span><b>One useful answer</b><small>Made for your question</small></span>
              <span className="landing-mini-check"><Check size={13} /></span>
            </motion.div>
          </motion.div>
        </section>

        <section className="landing-capability-strip" id="capabilities" aria-label="Goldmine capabilities">
          <span>ONE WORKSPACE FOR</span>
          <div><MessageSquare size={16} /> Everyday chat</div>
          <i />
          <div><BookOpen size={16} /> Study help</div>
          <i />
          <div><Globe size={16} /> Web research</div>
          <i />
          <div><FileImage size={16} /> Your files</div>
        </section>

        <section className="landing-section landing-how" id="how-it-works">
          <motion.div className="landing-section-heading" initial="hidden" whileInView="visible" viewport={{ once: true, amount: 0.45 }} variants={riseIn} transition={{ duration: 0.65, ease: [0.22, 1, 0.36, 1] }}>
            <span className="landing-section-kicker">A smarter flow</span>
            <h2>One question. A more considered answer.</h2>
            <p>Goldmine adapts to what you ask, so simple questions stay simple and bigger ones get a deeper look.</p>
          </motion.div>
          <div className="landing-feature-grid">
            {features.map((feature, index) => (
              <motion.article
                key={feature.number}
                className="landing-feature-card"
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, amount: 0.25 }}
                variants={riseIn}
                transition={{ duration: 0.65, delay: index * 0.1, ease: [0.22, 1, 0.36, 1] }}
              >
                <div className="landing-feature-top"><span className="landing-feature-icon"><feature.icon size={19} /></span><span>{feature.number}</span></div>
                <h3>{feature.title}</h3>
                <p>{feature.desc}</p>
                <div className="landing-feature-line" />
              </motion.article>
            ))}
          </div>
        </section>

        <section className="landing-cta-section">
          <motion.div className="landing-cta-panel" initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.35 }} transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}>
            <div className="landing-cta-glow" />
            <div className="landing-cta-mark"><GoldmineLogo size="small" /></div>
            <span className="landing-section-kicker">Your next question starts here</span>
            <h2>Think better, together.</h2>
            <p>Open Goldmine and see where your curiosity takes you.</p>
            <Button asChild size="lg" className="landing-primary-cta">
              <Link to="/auth">Get started <ArrowRight size={17} /></Link>
            </Button>
          </motion.div>
        </section>
      </main>

      <footer className="landing-footer">
        <Link to="/" className="landing-brand"><GoldmineLogo size="small" /><span>Goldmine<span className="landing-brand-ai"> AI</span></span></Link>
        <span>© {currentYear} Goldmine AI</span>
        <Link to="/auth">Start chatting <ArrowRight size={14} /></Link>
      </footer>
    </div>
  );
}
