import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import ChatDashboard from './pages/ChatDashboard';
import DetailedResults from './pages/DetailedResults';
import Wizard from './pages/Wizard';
import About from './pages/About';
import Contact from './pages/Contact';
import Roadmap from './pages/Roadmap';
import Login from './pages/Auth/Login';
import Register from './pages/Auth/Register';
import MindMap from './pages/MindMap';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={<Home />} />
          <Route path="/about" element={<About />} />
          <Route path="/contact" element={<Contact />} />
          <Route path="/roadmap" element={<Roadmap />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* Protected Routes */}
          <Route path="/wizard" element={<ProtectedRoute><Wizard /></ProtectedRoute>} />
          <Route path="/chat" element={<ProtectedRoute><ChatDashboard /></ProtectedRoute>} />
          <Route path="/results" element={<ProtectedRoute><DetailedResults /></ProtectedRoute>} />
          <Route path="/mindmap" element={<ProtectedRoute><MindMap /></ProtectedRoute>} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
