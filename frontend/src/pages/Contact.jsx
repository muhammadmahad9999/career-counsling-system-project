import React, { useState } from 'react';
import Navbar from '../components/Navbar';
import { Mail, MapPin, Phone } from 'lucide-react';

const Contact = () => {
    const [status, setStatus] = useState('');

    const handleSubmit = (e) => {
        e.preventDefault();
        setStatus('Sent!');
        setTimeout(() => setStatus(''), 2000);
    }

    return (
        <div className="min-h-screen bg-dark text-white font-grotesk">
            <Navbar />

            <div className="pt-24 px-6 md:px-20 max-w-6xl mx-auto">
                <div className="grid md:grid-cols-2 gap-16">

                    {/* Info */}
                    <div>
                        <h1 className="text-4xl md:text-5xl font-bold mb-6">Get in <span className="text-accent-teal">Touch</span></h1>
                        <p className="text-text-gray text-lg mb-10">
                            Have questions about your career path? Need help with the platform? We're here to assist you.
                        </p>

                        <div className="space-y-6">
                            <div className="flex items-center gap-4 bg-card-bg p-4 rounded-xl border border-card-border">
                                <div className="w-12 h-12 bg-primary-cyan/20 rounded-full flex items-center justify-center text-primary-cyan"><Mail size={24} /></div>
                                <div>
                                    <p className="text-sm text-gray-400">Email Us</p>
                                    <p className="font-bold">support@futurepath.pk</p>
                                </div>
                            </div>
                            <div className="flex items-center gap-4 bg-card-bg p-4 rounded-xl border border-card-border">
                                <div className="w-12 h-12 bg-accent-teal/20 rounded-full flex items-center justify-center text-accent-teal"><Phone size={24} /></div>
                                <div>
                                    <p className="text-sm text-gray-400">Call Us</p>
                                    <p className="font-bold">+92 300 1234567</p>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Form */}
                    <form onSubmit={handleSubmit} className="bg-card-bg border border-card-border p-8 rounded-3xl shadow-2xl relative overflow-hidden">
                        <div className="absolute top-0 right-0 w-32 h-32 bg-primary-cyan/10 rounded-full blur-[40px] pointer-events-none" />

                        <div className="space-y-6 relative z-10">
                            <div>
                                <label className="block text-sm text-gray-400 mb-2">Name</label>
                                <input type="text" className="w-full bg-dark border border-gray-700 rounded-xl p-4 focus:border-primary-cyan outline-none" required />
                            </div>
                            <div>
                                <label className="block text-sm text-gray-400 mb-2">Email</label>
                                <input type="email" className="w-full bg-dark border border-gray-700 rounded-xl p-4 focus:border-primary-cyan outline-none" required />
                            </div>
                            <div>
                                <label className="block text-sm text-gray-400 mb-2">Message</label>
                                <textarea className="w-full bg-dark border border-gray-700 rounded-xl p-4 focus:border-primary-cyan outline-none h-32 resize-none" required></textarea>
                            </div>

                            <button type="submit" className="w-full bg-primary-cyan text-dark font-bold py-4 rounded-xl hover:bg-cyan-400 transition-colors">
                                {status || 'Send Message'}
                            </button>
                        </div>
                    </form>

                </div>
            </div>
        </div>
    );
};

export default Contact;
