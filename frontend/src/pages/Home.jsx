import React from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import Navbar from '../components/Navbar';

const Home = () => {
    const navigate = useNavigate();

    return (
        <div className="min-h-screen w-full flex flex-col justify-center items-center relative overflow-hidden bg-dark">
            {/* Background Gradients */}
            <div className="absolute top-[-10%] right-[-10%] w-[50vw] h-[50vw] bg-primary-cyan/20 rounded-full blur-[120px] pointer-events-none" />
            <div className="absolute bottom-[-10%] left-[-10%] w-[40vw] h-[40vw] bg-blue-600/20 rounded-full blur-[100px] pointer-events-none" />

            <Navbar />

            <div className="z-10 text-center max-w-4xl px-4 mt-20">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8 }}
                    className="mb-6"
                >
                    <h1 className="text-5xl md:text-7xl font-bold font-grotesk leading-tight text-white mb-6 drop-shadow-lg">
                        Your Future <br />
                        <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary-cyan to-accent-teal">
                            Starts Here.
                        </span>
                    </h1>

                    <p className="text-lg md:text-xl text-text-gray max-w-2xl mx-auto leading-relaxed mb-4">
                        AI-powered career counselling for FSc students in Pakistan.
                    </p>
                    <p className="text-md text-text-gray/80 max-w-xl mx-auto">
                        Get personalized guidance, roadmaps, and motivation.
                    </p>
                </motion.div>
 
                <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.3, duration: 0.5 }}
                    className="flex justify-center items-center mt-12"
                >
                    <button
                        onClick={() => navigate('/wizard')}
                        className="group relative px-10 py-5 bg-gradient-to-r from-primary-cyan to-accent-teal text-dark font-extrabold rounded-2xl overflow-hidden transition-all hover:scale-105 hover:shadow-[0_0_30px_rgba(0,229,255,0.5)] w-72 text-lg"
                    >
                        <span className="relative z-10 flex items-center justify-center gap-2">
                            Start Test <span>→</span>
                        </span>
                    </button>
                </motion.div>
            </div>

            {/* Features / Why Section Preview */}
            <div className="absolute bottom-10 w-full text-center text-gray-500 text-sm animate-bounce">
                Scroll for more
            </div>
        </div>
    );
};

export default Home;
