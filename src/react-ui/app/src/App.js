import React from "react";
import {
  BrowserRouter as Router,
  Route,
  Switch,
  Redirect,
} from "react-router-dom";
import LoginForm from "./components/LoginForm";
import JarvisPage from "./components/JarvisPage";
import AuthContext from "./context/AuthContext";
import PrivateRoute from "./PrivateRoute";

function App() {
  const [isLoggedIn, setIsLoggedIn] = React.useState(false);

  return (
    <AuthContext.Provider value={{ isLoggedIn, setIsLoggedIn }}>
      <Router>
        <Switch>
          <Route path="/login" component={LoginForm} />
          <PrivateRoute path="/jarvis" component={JarvisPage} />
          <Redirect from="/" to="/login" />
        </Switch>
      </Router>
    </AuthContext.Provider>
  );
}

export default App;
