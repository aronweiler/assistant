import styles from "./LoginForm.module.css";
import React, { useState } from "react";
//import { useContext } from 'react';
//import { AuthContext } from '../context/AuthContext';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from "react-router-dom";

function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();  

  //const { setIsLoggedIn } = useContext(AuthContext);
  const { setIsLoggedIn } = useAuth();

  const login = async (email, password) => {
    try {
      const apiUrl = `http://${process.env.REACT_APP_API_USER_HOST}:${process.env.REACT_APP_API_USER_PORT}`;
      console.log("API URL:", apiUrl);
      const formData = new URLSearchParams();
      formData.append("username", email);
      formData.append("password", password);

      const response = await fetch(`${apiUrl}/token`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: formData,
      });
      if (!response.ok) throw new Error("Login failed");
      const data = await response.json();
      localStorage.setItem("token", data.access_token);      
      console.log("Login successful, token set in local storage");

      setIsLoggedIn(true);
      console.log("Calling setIsLoggedIn:", true);

      const token_test = localStorage.getItem('token');
      console.log('Token from storage:', token_test);      

      console.log('Calling page:', localStorage.getItem('callingPage'));
      // After setting the token in localStorage
      navigate(localStorage.getItem('callingPage') || '/');

    } catch (error) {
      console.error("Login error:", error);
      setError(error.message);
    }
  };

  const handleSubmit = async (e) => {
    console.log("Login form submitted");

    e.preventDefault();
    await login(email, password);
  };

  return (
    <div className={styles["form-container"]}>
      <form onSubmit={handleSubmit}>
        <label>
          User Name:
          <input
            type="text"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>
        <label>
          Password:
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        {error && <div style={{ color: "red" }}>{error}</div>}
        <button type="submit">Login</button>
      </form>
    </div>
  );
}

export default LoginForm;
