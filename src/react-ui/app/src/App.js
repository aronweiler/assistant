import React from "react";
import {
  BrowserRouter as Router,
  Route,
  Routes,
  Navigate,
} from "react-router-dom";
import LandingPage from "./components/LandingPage";
import LoginForm from "./components/LoginForm";
import JarvisPage from "./components/JarvisPage";
import PrivateRoute from "./PrivateRoute";
import { AuthProvider } from "./context/AuthContext";

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginForm />} />
          <Route path="/jarvis" element={<JarvisPage />} />
          {/* <Route path="/jarvis" element={<PrivateRoute><JarvisPage /></PrivateRoute>}/> */}
          <Route path="*" element={<Navigate replace to="/" />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
