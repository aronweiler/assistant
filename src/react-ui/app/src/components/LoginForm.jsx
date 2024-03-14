import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

function LoginForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const login = async (email, password) => {
    try {
      const apiUrl = `http://${process.env.REACT_APP_API_USER_HOST}:${process.env.REACT_APP_API_USER_PORT}`;
      const response = await fetch(`${apiUrl}/token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username: email, password }),
      });
      if (!response.ok) throw new Error('Login failed');
      const data = await response.json();
      localStorage.setItem('token', data.access_token);
      navigate('/'); // Redirect to the calling page or home page
    } catch (error) {
      console.error('Login error:', error);
      setError(error.message);
    }
  };

  const handleSubmit = async (e) => {
    console.log('Login form submitted');

    e.preventDefault();
    await login(email, password);
  };

  return (
    <form onSubmit={handleSubmit}>
      <label>
        Email:
        <input
          type='email'
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
      </label>
      <label>
        Password:
        <input
          type='password'
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </label>
      {error && <div style={{ color: 'red' }}>{error}</div>}
      <button type='submit'>Login</button>
    </form>
  );
}

export default LoginForm;