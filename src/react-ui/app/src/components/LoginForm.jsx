import React, { useState } from "react";

function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const login = async (email, password) => {
    try {
      const apiUrl = `http://${process.env.REACT_APP_API_USER_HOST}:${process.env.REACT_APP_API_USER_PORT}`;
      const response = await fetch(`${apiUrl}/token`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ username: email, password }),
      });
      if (!response.ok) throw new Error("Login failed");
      const data = await response.json();
      localStorage.setItem("token", data.access_token);
      // Redirect or update UI as logged in
    } catch (error) {
      console.error("Login error:", error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    login(email, password);
  };

  return (
    <form onSubmit={handleSubmit}>
      <label>
        Email:
        <input
          type="email"
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
      <button type="submit">Login</button>
    </form>
  );
}

export default LoginForm;
