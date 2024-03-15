import React from "react";
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

function JarvisPage() {
  const navigate = useNavigate();

  // Set the calling page in local storage
  localStorage.setItem("callingPage", "/jarvis");

  useEffect(() => {
    console.log("Checking for token...");

    const token = localStorage.getItem("token");
    // TODO: Validate token
    

    console.log("Token:", token);

    if (!token) {
      console.log("No token found, redirecting to login");
      navigate("/login");
    }
  }, [navigate]);

  console.log("Rendering JarvisPage...");
  return (
    <div>
      <h1>Hey Jarvis...</h1>
    </div>
  );
}

export default JarvisPage;
