import React from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowRight,
  Brain,
  Compass,
  BookOpen,
  Award,
  TrendingUp,
  MessageSquareText,
  Sparkles,
  GraduationCap,
  Target,
  Cpu
} from "lucide-react";
import Navbar from "../components/Navbar";

const Home = () => {
  const navigate = useNavigate();

  // Animation variants
  const fadeIn = {
    hidden: { opacity: 0, y: 25 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.6 } }
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { staggerChildren: 0.15 }
    }
  };

  const streams = [
    {
      name: "Pre-Engineering",
      desc: "Mathematics, Physics & Chemistry. Transition into Aerospace, Software, Robotics, or Civil Engineering.",
      bg: "from-cyan-500/10 to-blue-500/5",
      border: "border-cyan-500/20 text-primary-cyan"
    },
    {
      name: "Pre-Medical",
      desc: "Biology, Chemistry & Physics. Chart a path in Medicine (MBBS/BDS), Biotechnology, Genetics, or Pharmacy.",
      bg: "from-rose-500/10 to-orange-500/5",
      border: "border-rose-500/20 text-rose-400"
    },
    {
      name: "ICS (Computer Science)",
      desc: "Computer Science, Math & Physics. Explore Cybersecurity, AI & ML, Game Dev, or Software Engineering.",
      bg: "from-emerald-500/10 to-teal-500/5",
      border: "border-emerald-500/20 text-accent-teal"
    },
    {
      name: "Arts & Commerce",
      desc: "Business, Finance, Humanities & Design. Step into Actuarial Science, Data Analytics, LLB, or Creative Arts.",
      bg: "from-purple-500/10 to-fuchsia-500/5",
      border: "border-purple-500/20 text-purple-400"
    }
  ];

  return (
    <div className="min-h-screen bg-dark text-white font-grotesk overflow-y-auto selection:bg-primary-cyan/30">
      <Navbar />

      {/* Hero Section */}
      <header className="relative w-full min-h-screen flex flex-col justify-center items-center px-4 pt-32 pb-36 overflow-hidden bg-hero-gradient">
        {/* Background Gradients */}
        <div className="absolute top-[-10%] right-[-10%] w-[50vw] h-[50vw] bg-primary-cyan/15 rounded-full blur-[130px] pointer-events-none animate-drift-slow" />
        <div className="absolute bottom-[-10%] left-[-10%] w-[40vw] h-[40vw] bg-blue-600/15 rounded-full blur-[110px] pointer-events-none animate-drift-slower" />

        <div className="z-10 text-center max-w-4xl px-4 mt-8 relative">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8 }}
            className="inline-flex items-center gap-2 rounded-full border border-primary-cyan/20 bg-primary-cyan/10 px-4 py-2 text-xs md:text-sm text-primary-cyan mb-8"
          >
            <Sparkles size={14} className="animate-pulse" />
            Empowering Pakistani FSc Students with Machine Learning
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.1 }}
            className="mb-8"
          >
            <h1 className="text-5xl md:text-8xl font-extrabold leading-[1.1] text-white tracking-tight drop-shadow-xl">
              Your Future <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary-cyan via-cyan-300 to-accent-teal">
                Starts Here.
              </span>
            </h1>

            <p className="text-lg md:text-2xl text-text-gray max-w-2xl mx-auto leading-relaxed mt-8">
              AI-powered career counselling designed specifically for intermediate students in Pakistan.
            </p>
            <p className="text-sm md:text-base text-text-gray/70 max-w-xl mx-auto mt-4">
              Discover your natural strengths, get personalized roadmaps, and chat with Roshni, your AI mentor.
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4, duration: 0.6 }}
            className="flex flex-col sm:flex-row justify-center items-center gap-6 mt-12 w-full max-w-xl mx-auto"
          >
            <button
              onClick={() => navigate("/wizard")}
              className="group h-14 w-64 bg-gradient-to-r from-primary-cyan to-accent-teal text-dark font-extrabold rounded-2xl flex items-center justify-center gap-2 transition-all hover:scale-105 hover:shadow-[0_0_35px_rgba(0,229,255,0.4)] text-base md:text-lg"
            >
              Start Free Assessment <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
            </button>
            <a
              href="#features"
              className="group h-14 w-64 border border-white/10 hover:border-white/20 hover:bg-white/5 text-white font-semibold rounded-2xl flex items-center justify-center gap-2 transition-all hover:scale-105 text-base md:text-lg"
            >
              Learn How It Works
            </a>
          </motion.div>
        </div>

        {/* Scroll indicator */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 text-gray-500 text-xs flex flex-col items-center gap-2 opacity-80">
          <span className="uppercase tracking-[0.2em]">Scroll for details</span>
          <span className="w-1.5 h-6 rounded-full border border-gray-600 flex justify-center py-0.5">
            <span className="w-0.5 h-1.5 bg-gray-500 rounded-full animate-bounce"></span>
          </span>
        </div>
      </header>

      {/* Stats Counter Section */}
      <section className="border-y border-white/5 bg-card-bg/30 py-10 relative z-10">
        <div className="max-w-7xl mx-auto px-4 md:px-8 grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
          {[
            { value: "4+", label: "FSc Streams Covered" },
            { value: "100%", label: "Privacy Ensured" },
            { value: "Hybrid ML", label: "Stacking Classifier" },
            { value: "< 2s", label: "Fast prediction" }
          ].map((stat, idx) => (
            <div key={idx} className="space-y-1">
              <p className="text-3xl md:text-4xl font-extrabold text-primary-cyan">{stat.value}</p>
              <p className="text-xs md:text-sm text-text-gray font-medium">{stat.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-24 max-w-7xl mx-auto px-4 md:px-8 relative z-10 scroll-mt-20">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-xs uppercase tracking-[0.3em] text-accent-teal mb-3 font-bold">Comprehensive Pipeline</h2>
          <p className="text-3xl md:text-5xl font-extrabold text-white">How FuturePath Empowers You</p>
          <p className="text-text-gray mt-4 text-sm md:text-base">
            We use scientific measurements to analyze your aptitude, personality, and interests, mapping them to the top careers in Pakistan.
          </p>
        </div>

        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          className="grid md:grid-cols-3 gap-8"
        >
          {/* Card 1: Stacking Machine Learning */}
          <motion.div
            variants={fadeIn}
            className="bg-card-bg border border-card-border hover:border-primary-cyan/40 rounded-[32px] p-8 transition-all hover:translate-y-[-4px]"
          >
            <div className="p-4 w-fit rounded-2xl bg-primary-cyan/10 text-primary-cyan mb-6">
              <Cpu size={24} />
            </div>
            <h3 className="text-xl font-bold mb-3">Hybrid ML Classifier</h3>
            <p className="text-sm text-text-gray leading-relaxed">
              Our backend matches your scores using a robust Stacking Classifier containing Logistic Regression, Random Forest, and XGBoost models trained on intermediate demographics.
            </p>
          </motion.div>

          {/* Card 2: Interactive Roadmaps */}
          <motion.div
            variants={fadeIn}
            className="bg-card-bg border border-card-border hover:border-accent-teal/40 rounded-[32px] p-8 transition-all hover:translate-y-[-4px]"
          >
            <div className="p-4 w-fit rounded-2xl bg-accent-teal/10 text-accent-teal mb-6">
              <Compass size={24} />
            </div>
            <h3 className="text-xl font-bold mb-3">Custom Career Roadmaps</h3>
            <p className="text-sm text-text-gray leading-relaxed">
              Get an interactive visual flowchart mapped with specific skills to build, local university matching, required entry test milestones, and market statistics.
            </p>
          </motion.div>

          {/* Card 3: Real-time Counselor */}
          <motion.div
            variants={fadeIn}
            className="bg-card-bg border border-card-border hover:border-rose-500/40 rounded-[32px] p-8 transition-all hover:translate-y-[-4px]"
          >
            <div className="p-4 w-fit rounded-2xl bg-rose-500/10 text-rose-400 mb-6">
              <MessageSquareText size={24} />
            </div>
            <h3 className="text-xl font-bold mb-3">Voice-Enabled AI Chat</h3>
            <p className="text-sm text-text-gray leading-relaxed">
              Ask Roshni, our AI counselor, about scholarships, course materials, or admission schedules. Featuring live-streaming speech recognition and active search capabilities.
            </p>
          </motion.div>
        </motion.div>
      </section>

      {/* FSc Streams Section */}
      <section className="py-20 bg-dark-secondary/5 relative z-10 border-y border-white/5">
        <div className="max-w-7xl mx-auto px-4 md:px-8">
          <div className="flex flex-col lg:flex-row gap-12 items-center">
            <div className="lg:w-1/3 space-y-4">
              <h2 className="text-xs uppercase tracking-[0.3em] text-primary-cyan font-bold">Tailored Framework</h2>
              <p className="text-3xl md:text-5xl font-extrabold text-white">Stream-Specific Insights</p>
              <p className="text-text-gray text-sm md:text-base leading-relaxed">
                Whether you're currently in Pre-Engineering, Pre-Medical, ICS, or Arts, FuturePath maps your specific curriculum subjects to professional university degrees.
              </p>
            </div>
            <div className="lg:w-2/3 grid sm:grid-cols-2 gap-6 w-full">
              {streams.map((s, i) => (
                <div
                  key={i}
                  className={`bg-gradient-to-br ${s.bg} border ${s.border} rounded-3xl p-6 hover:scale-[1.02] transition-transform`}
                >
                  <h3 className="text-lg font-bold mb-2 text-white">{s.name}</h3>
                  <p className="text-xs md:text-sm text-text-gray leading-relaxed">{s.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* About Section */}
      <section className="py-24 max-w-7xl mx-auto px-4 md:px-8 relative z-10 scroll-mt-20">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          <div className="space-y-6">
            <div className="inline-flex items-center gap-2 rounded-full border border-accent-teal/20 bg-accent-teal/10 px-4 py-1.5 text-xs text-accent-teal">
              <GraduationCap size={14} />
              Our Mission
            </div>
            <h2 className="text-3xl md:text-5xl font-extrabold text-white leading-tight">
              Bridging the Counselling Gap for Pakistan's Youth
            </h2>
            <p className="text-text-gray text-sm md:text-base leading-relaxed">
              Every year, over a million intermediate students graduate in Pakistan. Yet, a vast majority choose their career paths purely based on societal pressure, peer choices, or incomplete market metrics. 
            </p>
            <p className="text-text-gray text-sm md:text-base leading-relaxed">
              <strong>FuturePath</strong> was built as an academic research and engineering platform to democratize quality career advice. By combining advanced Machine Learning algorithms with psychometrics (Big Five Personality Framework and Holland's RIASEC Codes), we help students identify where their natural strengths, interests, and academic records intersect.
            </p>
            <div className="grid grid-cols-2 gap-4 pt-2">
              <div className="flex gap-2">
                <Target className="text-primary-cyan shrink-0 mt-1" size={18} />
                <div>
                  <h4 className="font-semibold text-sm text-white">Objective Guidance</h4>
                  <p className="text-xs text-text-gray mt-1">Based on concrete data, not guesswork.</p>
                </div>
              </div>
              <div className="flex gap-2">
                <BookOpen className="text-accent-teal shrink-0 mt-1" size={18} />
                <div>
                  <h4 className="font-semibold text-sm text-white">Comprehensive Tests</h4>
                  <p className="text-xs text-text-gray mt-1">Measuring aptitude, personality, and RIASEC interests.</p>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-card-bg border border-card-border rounded-[36px] p-8 md:p-10 relative overflow-hidden">
            <div className="absolute top-0 right-0 w-48 h-48 bg-primary-cyan/5 blur-3xl rounded-full" />
            <h3 className="text-xl font-bold text-white mb-6">How Your Data is Evaluated</h3>
            <div className="space-y-6">
              {[
                {
                  step: "01",
                  title: "Aptitude Diagnostics",
                  desc: "Analyzes Logic, Math, Verbal, and Spatial reasoning through problem solving."
                },
                {
                  step: "02",
                  title: "Big Five Personality Trait Mapping",
                  desc: "Evaluates Openness, Conscientiousness, Extraversion, Agreeableness, and Neuroticism."
                },
                {
                  step: "03",
                  title: "Holland Codes (RIASEC)",
                  desc: "Measures occupational interests across Realistic, Investigative, Artistic, Social, Enterprising, and Conventional archetypes."
                }
              ].map((item, idx) => (
                <div key={idx} className="flex gap-4">
                  <span className="text-2xl font-black text-primary-cyan/20 font-mono tracking-tighter">
                    {item.step}
                  </span>
                  <div>
                    <h4 className="font-bold text-sm text-white">{item.title}</h4>
                    <p className="text-xs text-text-gray mt-1">{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Call To Action */}
      <section className="py-20 bg-gradient-to-r from-cyan-950/40 via-dark to-teal-950/40 border-t border-white/5 relative z-10 text-center">
        <div className="max-w-4xl mx-auto px-4 space-y-6">
          <h2 className="text-3xl md:text-5xl font-extrabold text-white">Ready to Shape Your Career Roadmap?</h2>
          <p className="text-text-gray max-w-xl mx-auto text-sm md:text-base">
            Take our 10-minute diagnostic assessment to receive your custom Machine Learning model prediction and personalized counseling session.
          </p>
          <div className="pt-4 flex justify-center">
            <button
              onClick={() => navigate("/wizard")}
              className="px-10 py-5 bg-gradient-to-r from-primary-cyan to-accent-teal text-dark font-extrabold rounded-2xl hover:scale-105 hover:shadow-[0_0_30px_rgba(0,229,255,0.4)] transition-all flex items-center gap-2 text-base md:text-lg"
            >
              Start Assessment Now <ArrowRight size={18} />
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
          <div className="flex justify-center gap-6 pt-2 text-text-gray">
            <a href="/about" className="hover:text-primary-cyan transition-colors">
              About
            </a>
            <a href="/contact" className="hover:text-primary-cyan transition-colors">
              Contact
            </a>
            <a href="/roadmap" className="hover:text-primary-cyan transition-colors">
              General Roadmap
            </a>
          </div>
          <p className="pt-6 border-t border-white/5 mt-6">
            &copy; {new Date().getFullYear()} FuturePath AI. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
};

export default Home;
