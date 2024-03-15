import { Link } from "react-router-dom";
import { useAuth } from '../context/AuthContext';

function LandingPage() {
  const { logout } = useAuth();

  return (
    <div>
      <h1>Hello World</h1>
      <Link to="/jarvis">Go to Jarvis Page</Link>
      <br />
      <button onClick={logout}>Logout</button>
    </div>
  );
}
export default LandingPage;
