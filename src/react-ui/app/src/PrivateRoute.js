import React from "react";
import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "./context/AuthContext";

const PrivateRoute = () => {
  console.log("PrivateRoute checking logged in status...");
  const { isLoggedIn } = useAuth();
  console.log("isLoggedIn:", isLoggedIn);
  return isLoggedIn ? <Outlet /> : <Navigate to='/login' />;
};

export default PrivateRoute;
