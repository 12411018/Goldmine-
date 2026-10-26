import { Link } from 'react-router-dom';
import { motion } from 'motion/react';
import { ArrowRight, ShieldCheck, Zap, Sparkles, Layers } from 'lucide-react';
import { Button } from '@/components/ui/button';
import GoldmineLogo from '@/components/brand/GoldmineLogo';

const currentYear = new Date().getFullYear();

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Navbar */}
      <header className="px-6 h-16 flex items-center border-b bg-background/80 backdrop-blur-md sticky top-0 z-50">
        <div className="flex items-center gap-2 font-semibold text-lg">
          <GoldmineLogo size="small" />
          <span>Goldmine AI</span>
        </div>
        <div className="ml-auto flex items-center gap-4">
          <Link to="/auth" className="text-sm font-medium hover:text-primary transition-colors">
            Log in
          </Link>
          <Button asChild size="sm">
            <Link to="/auth">Get Started</Link>
          </Button>
        </div>
      </header>

      <main className="flex-1">
        {/* Hero Section */}
        <section className="py-24 px-6 lg:px-8 max-w-6xl mx-auto flex flex-col items-center text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-sm font-medium mb-8">
              <Sparkles className="w-4 h-4" />
              <span>The future of multi-model AI</span>
            </div>
            
            <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6 text-balance">
              One question.<br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary to-amber-200">
                Multiple minds.
              </span><br />
              One better answer.
            </h1>
            
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto mb-10 text-balance">
              Goldmine AI compares multiple AI models, evaluates their responses, and helps you find the strongest answer based on evidence and agreement.
            </p>
            
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Button asChild size="lg" className="h-12 px-8 text-base">
                <Link to="/auth">
                  Start using Goldmine
                  <ArrowRight className="ml-2 w-5 h-5" />
                </Link>
              </Button>
            </div>
          </motion.div>
        </section>

        {/* Features */}
        <section className="py-24 bg-muted/30 border-y">
          <div className="max-w-6xl mx-auto px-6 lg:px-8">
            <div className="text-center mb-16">
              <h2 className="text-3xl font-bold mb-4">How Goldmine Works</h2>
              <p className="text-muted-foreground max-w-2xl mx-auto">
                We don't just rely on one model's confidence. We use cross-model evaluation to find the best response.
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-8">
              {[
                {
                  icon: Layers,
                  title: "Multi-Model Orchestration",
                  desc: "Your prompt is simultaneously sent to top-tier models like DeepSeek, Qwen, and Llama."
                },
                {
                  icon: ShieldCheck,
                  title: "Transparent Evaluation",
                  desc: "We evaluate responses based on cross-model agreement, evidence, and completeness—not hidden reasoning."
                },
                {
                  icon: Zap,
                  title: "The Goldmine Score",
                  desc: "You get the strongest response selected automatically, along with a clear explanation of why it won."
                }
              ].map((feature, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.1, duration: 0.5 }}
                  className="bg-background p-6 rounded-2xl border shadow-sm"
                >
                  <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-6">
                    <feature.icon className="w-6 h-6 text-primary" />
                  </div>
                  <h3 className="text-xl font-semibold mb-3">{feature.title}</h3>
                  <p className="text-muted-foreground leading-relaxed">
                    {feature.desc}
                  </p>
                </motion.div>
              ))}
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t py-12 px-6">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2 font-semibold">
            <GoldmineLogo size="small" />
            <span>Goldmine AI</span>
          </div>
          <p className="text-sm text-muted-foreground">
            © {currentYear} Goldmine AI. Built for the future.
          </p>
        </div>
      </footer>
    </div>
  );
}
