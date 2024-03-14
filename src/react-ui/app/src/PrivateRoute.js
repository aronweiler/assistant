import React from 'react';
import { Route, Redirect } from 'react-router-dom';
import { useAuth } from './context/AuthContext';

const PrivateRoute = ({ component: Component, ...rest }) => {
  const { isLoggedIn } = useAuth();

  return (
    <Route {...rest} render={(props) => (
      isLoggedIn ? <Component {...props} /> : <Redirect to="/login" />
    )} />
  );
};

export default PrivateRoute;