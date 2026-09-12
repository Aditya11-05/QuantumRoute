import Dashboard from "./pages/Dashboard";
import Analysis from "./pages/Analysis";

export default function App() {
  const path = window.location.pathname;

  if (path === "/analysis") {
    return <Analysis />;
  }

  return <Dashboard />;
}
