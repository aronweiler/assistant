import React from 'react';
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

function JarvisPage() {
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/login');
    }
  }, [navigate]);

  return (
    <div>
      <h1>Hey Jarvis...</h1>
    </div>
  );
}

export default JarvisPage;