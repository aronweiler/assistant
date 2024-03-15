import styles from "./LoginForm.module.css";
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

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

      const token_test = localStorage.getItem('token');
      console.log('Token from storage:', token_test);

      // Redirect to the calling page (or the home page if no calling page is set)
      if (localStorage.getItem("callingPage")) {
        console.log("Redirecting to calling page:", localStorage.getItem("callingPage"));
        navigate(localStorage.getItem("callingPage"));
      } else {
        console.log("Redirecting to home page");
        navigate("/");
      }
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
