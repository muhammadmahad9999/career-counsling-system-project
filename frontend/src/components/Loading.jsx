import React from 'react';

const Loading = () => {
    return (
        <div className="fixed inset-0 bg-dark z-50 flex flex-col items-center justify-center">
            <div className="relative w-24 h-24">
                <div className="absolute inset-0 border-4 border-gray-800 rounded-full"></div>
                <div className="absolute inset-0 border-4 border-primary-cyan rounded-full border-t-transparent animate-spin"></div>
                <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-accent-teal font-bold animate-pulse">AI</span>
                </div>
            </div>
            <p className="mt-6 text-text-gray animate-pulse">Analyzing your future path...</p>
        </div>
    );
};

export default Loading;
