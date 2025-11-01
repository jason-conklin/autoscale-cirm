import { NavLink } from "react-router-dom";

const Header = () => {
  return (
    <header className="header">
      <div className="header-title">
        <span role="img" aria-label="AutoScale">
          📈
        </span>
        <span>AutoScale CIRM</span>
      </div>
      <nav className="header-nav">
        <NavLink
          to="/"
          className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
        >
          Dashboard
        </NavLink>
        <NavLink
          to="/settings"
          className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
        >
          Settings
        </NavLink>
      </nav>
    </header>
  );
};

export default Header;

