import React from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Brain,
  Compass,
  Cpu,
  Database,
  Layers,
  Sparkles,
  BookOpen,
  Heart,
  ChevronRight,
  ShieldCheck,
  Zap,
  Globe
} from "lucide-react";
import Navbar from "../components/Navbar";

const About = () => {
  const navigate = useNavigate();

  // Framer Motion variants
  const fadeInUp = {
    hidden: { opacity: 0, y: 30 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.6 } }
  };

  const staggerContainer = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { staggerChildren: 0.15 }
    }
  };

  const techCards = [
    {
      icon: Cpu,
      title: "Stacking Classifier",
      color: "text-primary-cyan bg-primary-cyan/10",
      desc: "Our machine learning engine uses an ensemble stacking classifier (XGBoost, Random Forest, Logistic Regression) trained on historical intermediate scores to deliver high-accuracy matches."
    },
    {
      icon: Layers,
      title: "FastAPI Framework",
      color: "text-accent-teal bg-accent-teal/10",
      desc: "A high-performance Python ASGI backend handling career inference, SHAP explainability calculations, and automated PDF report generation in milliseconds."
    },
    {
      icon: Database,
      title: "Supabase & SQLite",
      color: "text-purple-400 bg-purple-500/10",
      desc: "Utilizes robust database syncing to track past assessments, entry test scorecards, and custom resource bookmarks."
    },
    {
      icon: Globe,
      title: "Speech Recognition API",
      color: "text-rose-400 bg-rose-500/10",
      desc: "Integrates Web Speech API and Groq Whisper fallback to allow real-time voice conversations with Roshni, our AI counselor."
    }
  ];

  const scienceCards = [
    {
      icon: Brain,
      title: "Big Five Personality (OCEAN)",
      desc: "Measures Openness, Conscientiousness, Extraversion, Agreeableness, and Neuroticism to understand the work environment that suits your natural behaviors."
    },
    {
      icon: Compass,
      title: "Holland Codes (RIASEC)",
      desc: "Evaluates your vocational interests across Realistic, Investigative, Artistic, Social, Enterprising, and Conventional categories to map you to fulfilling roles."
    },
    {
      icon: BookOpen,
      title: "Cognitive Aptitude Diagnostics",
      desc: "Tests Math, Logic, Verbal, and Spatial applied problem-solving skills to pinpoint academic core capabilities and growth opportunities."
    }
  ];

  return (
    <div className="min-h-screen bg-dark text-white font-grotesk overflow-y-auto selection:bg-primary-cyan/30">
      <Navbar />

      {/* Hero Section */}
      <section className="relative pt-32 pb-20 px-6 md:px-12 max-w-7xl mx-auto overflow-hidden">
        {/* Neon glow accents */}
        <div className="absolute top-[-10%] right-[-10%] w-[35vw] h-[35vw] bg-primary-cyan/10 rounded-full blur-[100px] pointer-events-none animate-drift-slow" />
        <div className="absolute bottom-[10%] left-[-10%] w-[30vw] h-[30vw] bg-accent-teal/10 rounded-full blur-[80px] pointer-events-none animate-drift-slower" />

        <div className="text-center max-w-4xl mx-auto relative z-10">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8 }}
            className="inline-flex items-center gap-2 rounded-full border border-primary-cyan/20 bg-primary-cyan/10 px-4 py-1.5 text-xs text-primary-cyan mb-6"
          >
            <Sparkles size={12} className="animate-pulse" />
            Democratizing Career Counselling
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.1 }}
            className="text-4xl md:text-6xl font-extrabold leading-tight text-white mb-6"
          >
            Empowering Your <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary-cyan to-accent-teal">
              Educational Journey.
            </span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="text-text-gray text-base md:text-xl max-w-3xl mx-auto leading-relaxed mt-4"
          >
            FuturePath is an advanced AI platform engineered to resolve the career guidance gap for FSc students in Pakistan, matching students to universities and degrees.
          </motion.p>
        </div>
      </section>

      {/* The Context / Mission Section */}
      <section className="py-16 max-w-7xl mx-auto px-6 md:px-12 relative z-10 border-t border-white/5">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="space-y-6"
          >
            <div className="p-3 w-fit rounded-2xl bg-primary-cyan/10 text-primary-cyan">
              <Zap size={24} />
            </div>
            <h2 className="text-3xl md:text-4xl font-bold">Why We Built FuturePath</h2>
            <p className="text-text-gray text-sm md:text-base leading-relaxed">
              Every year, over a million high school students in Pakistan take Intermediate board exams (FSc Pre-Medical, Pre-Engineering, ICS, Arts). Unfortunately, most decide their next academic step without scientific metrics, relying solely on grades or generic suggestions.
            </p>
            <p className="text-text-gray text-sm md:text-base leading-relaxed">
              We developed FuturePath as an objective, personalized guidance counselor. Our system calculates career matches by analyzing academic streams alongside psychometric assessments, and provides interactive, structured roadmaps detailing what skills to learn, what admission tests to target, and where to apply.
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="bg-card-bg border border-card-border rounded-[32px] p-8 md:p-10 relative overflow-hidden"
          >
            <div className="absolute top-[-20%] right-[-20%] w-64 h-64 bg-accent-teal/5 rounded-full blur-[60px]" />
            <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
              <ShieldCheck className="text-accent-teal" size={20} />
              Key Platform Advantages
            </h3>
            <ul className="space-y-4">
              {[
                { title: "No Assumptions", desc: "Predictions are driven by custom machine learning calculations trained on regional intermediate outcomes." },
                { title: "Dual Interest & Personality Check", desc: "Integrates both RIASEC vocational models and Big Five OCEAN inventories for accuracy." },
                { title: "Real-time AI Chat & Search", desc: "Conversational voice assistant Roshni queries live search for up-to-date admission deadlines." },
                { title: "100% Free & Open", desc: "Fully accessible with downloadable PDF assessment summaries for teachers and parents." }
              ].map((adv, i) => (
                <li key={i} className="flex gap-3">
                  <span className="text-primary-cyan font-bold mt-0.5">•</span>
                  <div>
                    <h4 className="font-bold text-sm text-white">{adv.title}</h4>
                    <p className="text-xs text-text-gray mt-1 leading-relaxed">{adv.desc}</p>
                  </div>
                </li>
              ))}
            </ul>
          </motion.div>
        </div>
      </section>

      {/* The Science Behind The Tests Section */}
      <section className="py-20 bg-dark-secondary/5 relative z-10 border-y border-white/5">
        <div className="max-w-7xl mx-auto px-6 md:px-12">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="text-xs uppercase tracking-[0.3em] text-accent-teal mb-3 font-bold">The Assessment Science</h2>
            <h3 className="text-3xl md:text-5xl font-extrabold text-white">Three Assessment Pillars</h3>
            <p className="text-text-gray mt-4 text-sm md:text-base">
              FuturePath guides you based on standard psychological, vocational, and cognitive diagnostics.
            </p>
          </div>

          <motion.div
            variants={staggerContainer}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            className="grid md:grid-cols-3 gap-8"
          >
            {scienceCards.map((sc, i) => (
              <motion.div
                key={i}
                variants={fadeInUp}
                className="bg-card-bg border border-card-border hover:border-accent-teal/40 rounded-[28px] p-6 transition-all hover:scale-[1.02]"
              >
                <div className="p-3 w-fit rounded-xl bg-accent-teal/10 text-accent-teal mb-5">
                  <sc.icon size={22} />
                </div>
                <h4 className="text-lg font-bold mb-2 text-white">{sc.title}</h4>
                <p className="text-xs md:text-sm text-text-gray leading-relaxed">{sc.desc}</p>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* Technology Stack Details */}
      <section className="py-20 max-w-7xl mx-auto px-6 md:px-12 relative z-10">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-xs uppercase tracking-[0.3em] text-primary-cyan mb-3 font-bold">Platform Architecture</h2>
          <h3 className="text-3xl md:text-5xl font-extrabold text-white">Our Technology Stack</h3>
          <p className="text-text-gray mt-4 text-sm md:text-base">
            Modern, secure, and fast. Engineered to handle predictions and calculations seamlessly.
          </p>
        </div>

        <motion.div
          variants={staggerContainer}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          className="grid md:grid-cols-2 lg:grid-cols-4 gap-6"
        >
          {techCards.map((tc, i) => (
            <motion.div
              key={i}
              variants={fadeInUp}
              className="bg-card-bg border border-card-border hover:border-primary-cyan/40 rounded-3xl p-6 transition-all"
            >
              <div className={`p-3 w-fit rounded-xl mb-5 ${tc.color}`}>
                <tc.icon size={20} />
              </div>
              <h4 className="font-bold text-white mb-2">{tc.title}</h4>
              <p className="text-xs text-text-gray leading-relaxed">{tc.desc}</p>
            </motion.div>
          ))}
        </motion.div>
      </section>

      {/* Call To Action */}
      <section className="py-20 bg-gradient-to-r from-cyan-950/20 via-dark to-teal-950/20 border-t border-white/5 relative z-10 text-center">
        <div className="max-w-4xl mx-auto px-6 space-y-6">
          <h2 className="text-3xl md:text-5xl font-extrabold text-white">Find Your Stream Alignment</h2>
          <p className="text-text-gray max-w-xl mx-auto text-sm md:text-base">
            Spend 10 minutes assessing your strengths to view recommendations generated by our Machine Learning stacking algorithm.
          </p>
          <div className="pt-4 flex justify-center">
            <button
              onClick={() => navigate("/wizard")}
              className="group h-14 w-64 bg-gradient-to-r from-primary-cyan to-accent-teal text-dark font-extrabold rounded-2xl flex items-center justify-center gap-2 transition-all hover:scale-105 hover:shadow-[0_0_30px_rgba(0,229,255,0.4)] text-base md:text-lg"
            >
              Start Free Assessment <ChevronRight size={18} className="group-hover:translate-x-1 transition-transform" />
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-dark border-t border-white/5 py-12 text-center text-xs text-text-gray/60 relative z-10">
        <div className="max-w-7xl mx-auto px-4 space-y-4">
          <p className="font-bold text-white text-sm">FuturePath AI</p>
          <p className="max-w-md mx-auto">
            A research-based predictive career counselling platform designed for high-school and intermediate students in Pakistan.
          </p>
          <p className="pt-4 border-t border-white/5 mt-4">
            &copy; {new Date().getFullYear()} FuturePath AI. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
};

export default About;
