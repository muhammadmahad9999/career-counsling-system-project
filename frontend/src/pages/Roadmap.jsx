import React, { useEffect, useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { ArrowRight, BookOpen, Briefcase, GraduationCap, MapPinned } from "lucide-react";
import { motion } from "framer-motion";

import Navbar from "../components/Navbar";
import { fetchRoadmap } from "../api";
import { loadPredictionSession } from "../session";

const iconMap = [BookOpen, BookOpen, GraduationCap, Briefcase];

const Roadmap = () => {
  const location = useLocation();
  const session = loadPredictionSession();
  const preferredCareer =
    location.state?.career ||
    session?.prediction?.primary_recommendation?.career ||
    session?.prediction?.recommendations?.[0]?.career ||
    "";

  const [career, setCareer] = useState(preferredCareer);
  const [roadmap, setRoadmap] = useState(session?.prediction?.primary_recommendation || null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!career) {
      return;
    }

    const loadRoadmap = async () => {
      setLoading(true);
      setError("");
      try {
        const data = await fetchRoadmap(career);
        setRoadmap(data);
      } catch (requestError) {
        setError(
          requestError?.response?.data?.detail || "Roadmap data could not be loaded for this career."
        );
      } finally {
        setLoading(false);
      }
    };

    loadRoadmap();
  }, [career]);

  const steps = useMemo(() => roadmap?.roadmap_steps || [], [roadmap]);

  return (
    <div className="min-h-screen bg-dark text-white font-grotesk overflow-x-hidden">
      <Navbar />

      <div className="pt-24 px-4 md:px-10 pb-16">
        <div className="max-w-7xl mx-auto space-y-8">
          <section className="bg-card-bg border border-card-border rounded-[34px] p-8 md:p-10">
            <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-6">
              <div>
                <p className="text-sm uppercase tracking-[0.3em] text-primary-cyan mb-3">
                  Personalized roadmap
                </p>
                <h1 className="text-4xl md:text-5xl font-bold mb-3">
                  {career || "Choose a recommended career"}
                </h1>
                <p className="text-text-gray max-w-3xl">
                  Discover your personalized roadmap step-by-step, including recommended subjects, universities, key skills, and expected salaries.
                </p>
              </div>

              <div className="flex flex-wrap gap-3">
                {session?.prediction?.recommendations?.map((item) => (
                  <button
                    key={item.career}
                    type="button"
                    onClick={() => setCareer(item.career)}
                    className={`px-4 py-2 rounded-full border transition-colors ${
                      career === item.career
                        ? "border-primary-cyan bg-primary-cyan/10 text-primary-cyan"
                        : "border-white/10 text-text-gray hover:text-white hover:border-white/20"
                    }`}
                  >
                    {item.career}
                  </button>
                ))}
              </div>
            </div>
          </section>

          {loading ? (
            <section className="bg-card-bg border border-card-border rounded-[32px] p-10 text-text-gray">
              Loading roadmap...
            </section>
          ) : null}

          {error ? (
            <section className="bg-rose-400/10 border border-rose-400/30 text-rose-100 rounded-[32px] p-6">
              {error}
            </section>
          ) : null}

          {roadmap ? (
            <>
              <section className="grid lg:grid-cols-[1.1fr_0.9fr] gap-8">
                <div className="bg-card-bg border border-card-border rounded-[32px] p-8">
                  <h2 className="text-2xl font-bold mb-4">Career description</h2>
                  <p className="text-text-gray leading-relaxed">
                    {roadmap.description || "No description available in the reference roadmap file."}
                  </p>
                </div>

                <div className="bg-card-bg border border-card-border rounded-[32px] p-8">
                  <div className="flex items-center gap-2 text-accent-teal mb-4">
                    <MapPinned size={20} />
                    <h2 className="text-2xl font-bold">Universities to explore</h2>
                  </div>
                  <div className="flex flex-wrap gap-3">
                    {(roadmap.top_universities || []).map((university) => (
                      <span
                        key={university}
                        className="px-4 py-2 rounded-full bg-accent-teal/10 text-accent-teal"
                      >
                        {university}
                      </span>
                    ))}
                  </div>
                </div>
              </section>

              <section className="relative">
                <div className="absolute left-[31px] top-6 bottom-6 w-px bg-gradient-to-b from-primary-cyan/40 to-transparent md:left-[51px]" />

                <div className="space-y-6">
                  {steps.map((stepText, index) => {
                    const Icon = iconMap[index] || Briefcase;
                    return (
                      <motion.article
                        key={stepText}
                        initial={{ opacity: 0, x: 32 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.08 }}
                        className="flex gap-5 items-start"
                      >
                        <div className="w-[64px] h-[64px] rounded-full border border-primary-cyan/30 bg-primary-cyan/10 flex items-center justify-center shrink-0 z-10">
                          <Icon size={24} className="text-primary-cyan" />
                        </div>

                        <div className="flex-1 bg-card-bg border border-card-border rounded-[28px] p-6">
                          <p className="text-sm uppercase tracking-[0.25em] text-primary-cyan mb-3">
                            Step {index + 1}
                          </p>
                          <p className="text-text-gray leading-relaxed">{stepText}</p>
                        </div>
                      </motion.article>
                    );
                  })}
                </div>
              </section>

              <section className="grid md:grid-cols-2 gap-8">
                <div className="bg-card-bg border border-card-border rounded-[32px] p-8">
                  <h2 className="text-2xl font-bold mb-5">Skills to build</h2>
                  <div className="flex flex-wrap gap-3">
                    {(roadmap.skills_required || []).map((skill) => (
                      <span
                        key={skill}
                        className="px-4 py-2 rounded-full bg-primary-cyan/10 text-primary-cyan"
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="bg-card-bg border border-card-border rounded-[32px] p-8 flex flex-col justify-between">
                  <div>
                    <h2 className="text-2xl font-bold mb-4">Need more guidance?</h2>
                    <p className="text-text-gray">
                      Open the AI counselor with this career in context and ask about admissions,
                      scholarships, or the best next step for your profile.
                    </p>
                  </div>
                  <Link
                    to="/chat"
                    state={{ career }}
                    className="mt-6 inline-flex items-center gap-2 text-primary-cyan font-semibold hover:text-cyan-300"
                  >
                    Continue to AI counselor
                    <ArrowRight size={18} />
                  </Link>
                </div>
              </section>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
};

export default Roadmap;
