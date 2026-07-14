import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { LogOut, User } from 'lucide-react';
import logoImg from '../assets/logo.png';

const Navbar = () => {
    const { user, signOut } = useAuth();
    const navigate = useNavigate();

    const handleSignOut = async () => {
        await signOut();
        navigate('/');
    };

    return (
        <nav className="w-full py-4 px-10 flex justify-between items-center fixed top-0 left-0 bg-transparent z-50 backdrop-blur-sm">
            <Link to="/" className="flex items-center">
                <img src={logoImg} alt="FuturePath Logo" className="h-16 w-auto object-contain" />
            </Link>

            <div className="hidden md:flex space-x-12 text-sm font-medium text-text-gray">
                <Link to="/" className="hover:text-primary-cyan transition-colors">Home</Link>
                <Link to="/mindmap" className="hover:text-primary-cyan transition-colors">Mind-Map</Link>
                <Link to="/about" className="hover:text-primary-cyan transition-colors">About</Link>
                <Link to="/contact" className="hover:text-primary-cyan transition-colors">Contact</Link>
            </div>

            <div className="hidden md:flex items-center space-x-6">
                {user ? (
                    <>
                        <div className="flex items-center space-x-2 text-gray-300">
                            <div className="w-8 h-8 rounded-full bg-gradient-to-r from-purple-500 to-blue-500 flex items-center justify-center">
                                <User className="w-4 h-4 text-white" />
                            </div>
                            <span className="text-sm font-medium">
                                {user.user_metadata?.full_name || user.email}
                            </span>
                        </div>
                        <button 
                            onClick={handleSignOut}
                            className="flex items-center space-x-2 text-sm text-gray-400 hover:text-white transition-colors"
                        >
                            <LogOut className="w-4 h-4" />
                            <span>Sign Out</span>
                        </button>
                        <Link to="/wizard" className="bg-gradient-to-r from-primary-cyan to-accent-teal text-dark font-bold py-2 px-6 rounded-full hover:shadow-[0_0_15px_rgba(0,229,255,0.5)] transition-all transform hover:scale-105">
                            Dashboard
                        </Link>
                    </>
                ) : (
                    <>
                        <Link to="/login" className="text-sm font-medium text-gray-300 hover:text-white transition-colors">
                            Sign In
                        </Link>
                        <Link to="/wizard" className="bg-gradient-to-r from-primary-cyan to-accent-teal text-dark font-bold py-2 px-6 rounded-full hover:shadow-[0_0_15px_rgba(0,229,255,0.5)] transition-all transform hover:scale-105">
                            Get Started
                        </Link>
                    </>
                )}
            </div>
        </nav>
    );
};

export default Navbar;
