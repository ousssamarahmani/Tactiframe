import Home from "./pages/Home";
import Workspace from "./pages/Workspace";

export default function App() {
  return window.location.pathname.startsWith("/workspace") ? <Workspace /> : <Home />;
}
