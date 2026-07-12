import React from 'react';
import Navbar from '../components/Navbar';
import { motion } from 'framer-motion';

const About = () => {
    return (
        <div className="min-h-screen bg-dark text-white font-grotesk overflow-hidden">
            <Navbar />

            <div className="pt-24 px-6 md:px-20 max-w-7xl mx-auto">
                <motion.div
                    initial={{ opacity: 0, y: 30 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8 }}
                    className="text-center mb-16"
                >
                    <h1 className="text-4xl md:text-6xl font-bold mb-6">Empowering Your <span className="text-primary-cyan">Future.</span></h1>
                    <p className="text-text-gray text-xl max-w-2xl mx-auto">
                        FuturePath uses advanced AI to analyze your academic strengths and personal interests, providing accurate career guidance for students in Pakistan.
                    </p>
                </motion.div>

                <div className="grid md:grid-cols-2 gap-12 items-center">
                    <motion.div
                        initial={{ opacity: 0, x: -50 }}
                        whileInView={{ opacity: 1, x: 0 }}
                        viewport={{ once: true }}
                        className="bg-card-bg border border-card-border p-8 rounded-3xl"
                    >
                        <h2 className="text-3xl font-bold mb-4">Our Mission</h2>
                        <p className="text-gray-300 leading-relaxed">
                            To bridge the gap between education and career success. We believe every student deserves personalized mentorship, regardless of their background. By leveraging localized data and AI, we help you make informed decisions about your professional life.
                        </p>
                    </motion.div>

                    <div className="relative">
                        <div className="absolute top-0 right-0 w-64 h-64 bg-accent-teal/20 rounded-full blur-[80px] pointer-events-none" />
                        <img src="https://images.unsplash.com/photo-1522202176988-66273c2fd55f?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80" alt="Students collaborating" className="rounded-2xl shadow-2xl skew-y-3 opacity-80 hover:opacity-100 transition-opacity border border-white/10" />
                    </div>
                </div>
            </div>
        </div>
    );
};

export default About;
