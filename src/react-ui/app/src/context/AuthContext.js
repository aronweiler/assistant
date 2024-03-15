import { createContext, useState, useContext, useEffect } from "react";

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  console.log("AuthProvider");
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    console.log("AuthProvider useEffect");
    const token = localStorage.getItem("token");
    if (token) {
      console.log("AuthProvider useEffect token found");
      // Optionally validate the token here
      setIsLoggedIn(true);
    }
  }, []);

  const login = (token) => {
    console.log("AuthProvider login");
    localStorage.setItem("token", token);
    setIsLoggedIn(true);
  };

  const logout = () => {
    console.log("AuthProvider logout");
    localStorage.removeItem("token");
    setIsLoggedIn(false);
  };

  const value = {
    isLoggedIn,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => useContext(AuthContext);