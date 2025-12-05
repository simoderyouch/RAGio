import logo from "../../assets/logo.svg";
import { Link, useLocation } from "react-router-dom";
import useAuthStore from "../../stores/authStore";
import { FaRegUserCircle } from "react-icons/fa";
import { GoHome, GoFileDirectory, GoStack, GoSignOut, GoChevronDown } from "react-icons/go";
import { useState, useRef, useEffect } from "react";

const NavBar = () => {
    const token = useAuthStore((state) => state.token);
    const user = useAuthStore((state) => state.user);
    const logout = useAuthStore((state) => state.logout);
    const [userDropMenu, setUserDropMenu] = useState(false);
    const dropdownRef = useRef(null);
    const location = useLocation();

    const handleLogout = () => {
        logout();
        setUserDropMenu(false);
    };

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setUserDropMenu(false);
            }
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const isActiveLink = (path) => location.pathname === path;

    const navLinks = [
        { path: "/", label: "Accueil", icon: <GoHome className="w-4 h-4" /> },
        { path: "/chatroom", label: "Documents", icon: <GoFileDirectory className="w-4 h-4" /> },
        { path: "/general-chat", label: "Chat Général", icon: <GoStack className="w-4 h-4" /> }
    ];

    return (
        <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-slate-100">
            <nav className="container max-w-6xl mx-auto flex justify-between items-center py-4 px-6">
                {/* Logo */}
                <Link to="/" className="flex items-center">
                    <img 
                        className="h-[4.4rem] w-auto -mb-4" 
                        src={logo} 
                        alt="HCP Logo" 
                    />
                </Link>

                {/* Navigation Links - Desktop */}
                <ul className="hidden md:flex items-center gap-1">
                    {navLinks.map((link) => (
                        <li key={link.path}>
                            <Link 
                                to={link.path}
                                className={`
                                    flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200
                                    ${isActiveLink(link.path)
                                        ? 'bg-primary/10 text-primary'
                                        : 'text-slate-600 hover:text-primary hover:bg-slate-50'
                                    }
                                `}
                            >
                                {link.icon}
                                {link.label}
                            </Link>
                        </li>
                    ))}
                </ul>

                {/* Auth Section */}
                <div className="flex items-center gap-3">
                    {token && user ? (
                        <div className="relative" ref={dropdownRef}>
                            <button 
                                className="flex items-center gap-3 px-4 py-2 rounded-xl bg-slate-50 hover:bg-slate-100 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary/20"
                                onClick={() => setUserDropMenu(!userDropMenu)}
                            >
                                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-primary/70 flex items-center justify-center text-white font-semibold text-sm">
                                    {user.first_name?.[0]?.toUpperCase() || user.user_name?.[0]?.toUpperCase()}
                                </div>
                                <span className="hidden sm:block text-sm font-medium text-slate-700">
                                    {user.user_name}
                                </span>
                                <GoChevronDown className={`w-4 h-4 text-slate-400 transition-transform duration-200 ${userDropMenu ? 'rotate-180' : ''}`} />
                            </button>

                            {/* Dropdown Menu */}
                            {userDropMenu && (
                                <div className="absolute right-0 mt-2 w-72 bg-white rounded-xl border border-slate-100 shadow-xl shadow-slate-200/50 overflow-hidden animate-fade-in">
                                    {/* User Info Header */}
                                    <div className="px-4 py-4 bg-gradient-to-r from-primary/5 to-primary/10 border-b border-slate-100">
                                        <div className="flex items-center gap-3">
                                            <div className="w-12 h-12 rounded-full bg-gradient-to-br from-primary to-primary/70 flex items-center justify-center text-white font-bold text-lg">
                                                {user.first_name?.[0]?.toUpperCase() || user.user_name?.[0]?.toUpperCase()}
                                            </div>
                                            <div>
                                                <p className="font-semibold text-slate-900">
                                                    {user.first_name} {user.last_name}
                                                </p>
                                                <p className="text-xs text-slate-500">
                                                    {user.email}
                                                </p>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Navigation Links */}
                                    <div className="p-2">
                                        {navLinks.map((link) => (
                                            <Link 
                                                key={link.path}
                                                to={link.path}
                                                onClick={() => setUserDropMenu(false)}
                                                className={`
                                                    flex items-center gap-3 px-4 py-3 rounded-lg text-sm transition-all duration-200
                                                    ${isActiveLink(link.path)
                                                        ? 'bg-primary/10 text-primary font-medium'
                                                        : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                                                    }
                                                `}
                                            >
                                                {link.icon}
                                                {link.label}
                                            </Link>
                                        ))}
                                    </div>

                                    {/* Logout */}
                                    <div className="p-2 border-t border-slate-100">
                                        <button 
                                            onClick={handleLogout}
                                            className="flex items-center gap-3 w-full px-4 py-3 rounded-lg text-sm text-red-600 hover:bg-red-50 transition-all duration-200"
                                        >
                                            <GoSignOut className="w-4 h-4" />
                                            Se déconnecter
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    ) : (
                        <div className="flex items-center gap-2">
                            <Link 
                                to="/user/login"
                                className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-primary transition-colors"
                            >
                                Se connecter
                            </Link>
                            <Link 
                                to="/user/register"
                                className="px-4 py-2 text-sm font-semibold text-white bg-primary hover:bg-primary/90 rounded-lg transition-all duration-200 shadow-sm shadow-primary/30 hover:shadow-md hover:shadow-primary/30"
                            >
                                S'inscrire
                            </Link>
                        </div>
                    )}
                </div>
            </nav>

            {/* Mobile Navigation */}
            <div className="md:hidden border-t border-slate-100">
                <ul className="flex items-center justify-around py-2 px-4">
                    {navLinks.map((link) => (
                        <li key={link.path}>
                            <Link 
                                to={link.path}
                                className={`
                                    flex flex-col items-center gap-1 px-4 py-2 rounded-lg text-xs font-medium transition-all duration-200
                                    ${isActiveLink(link.path)
                                        ? 'text-primary'
                                        : 'text-slate-500'
                                    }
                                `}
                            >
                                {link.icon}
                                <span>{link.label}</span>
                            </Link>
                        </li>
                    ))}
                </ul>
            </div>
        </header>
    );
};

export default NavBar;
