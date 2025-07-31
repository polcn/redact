import React, { useState, useRef, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

export const Navigation: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, signOut } = useAuth();
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSignOut = async () => {
    try {
      await signOut();
      navigate('/login');
    } catch (error) {
      console.error('Error signing out:', error);
    }
  };

  const isActive = (path: string) => {
    return location.pathname === path;
  };

  return (
    <nav className="nav-anthropic">
      <div className="container-anthropic">
        <div className="flex justify-between">
          <div className="flex items-center gap-xl">
            <Link to="/" className="text-primary" style={{ fontSize: 'var(--font-size-lg)', fontWeight: 500 }}>
              Document Redaction
            </Link>
            
            <div className="flex items-center gap-lg">
              <Link
                to="/documents"
                className={`nav-link ${isActive('/documents') ? 'nav-link-active' : ''}`}
              >
                Documents
              </Link>
              <Link
                to="/config"
                className={`nav-link ${isActive('/config') ? 'nav-link-active' : ''}`}
              >
                Configuration
              </Link>
            </div>
          </div>

          <div className="flex items-center gap-md">
            <div className="relative" ref={dropdownRef}>
              <button
                onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                className="btn-anthropic btn-anthropic-secondary"
                style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}
              >
                <span style={{ fontSize: 'var(--font-size-sm)' }}>
                  {user?.signInDetails?.loginId || 'User'}
                </span>
                <svg
                  width="12"
                  height="12"
                  viewBox="0 0 12 12"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                  style={{
                    transform: isDropdownOpen ? 'rotate(180deg)' : 'rotate(0deg)',
                    transition: 'transform 0.2s ease'
                  }}
                >
                  <path
                    d="M2.5 4.5L6 8L9.5 4.5"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </button>

              {isDropdownOpen && (
                <div
                  className="dropdown-menu"
                  style={{
                    position: 'absolute',
                    top: 'calc(100% + var(--space-sm))',
                    right: 0,
                    minWidth: '200px',
                    backgroundColor: 'white',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius-md)',
                    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
                    overflow: 'hidden',
                    zIndex: 1000
                  }}
                >
                  <button
                    onClick={() => {
                      navigate('/quarantine');
                      setIsDropdownOpen(false);
                    }}
                    className="dropdown-item"
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      width: '100%',
                      padding: 'var(--space-sm) var(--space-md)',
                      border: 'none',
                      backgroundColor: 'transparent',
                      textAlign: 'left',
                      cursor: 'pointer',
                      fontSize: 'var(--font-size-sm)',
                      color: 'var(--color-text-primary)',
                      transition: 'background-color 0.2s ease'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--color-bg-secondary)'}
                    onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                  >
                    <span>Quarantine</span>
                    <span
                      style={{
                        fontSize: 'var(--font-size-xs)',
                        color: 'var(--accent-orange)',
                        backgroundColor: 'var(--color-bg-tertiary)',
                        padding: '2px 8px',
                        borderRadius: 'var(--radius-sm)'
                      }}
                    >
                      🗂️
                    </span>
                  </button>
                  
                  <div style={{ borderTop: '1px solid var(--color-border)' }} />
                  
                  <button
                    onClick={() => {
                      handleSignOut();
                      setIsDropdownOpen(false);
                    }}
                    className="dropdown-item"
                    style={{
                      display: 'block',
                      width: '100%',
                      padding: 'var(--space-sm) var(--space-md)',
                      border: 'none',
                      backgroundColor: 'transparent',
                      textAlign: 'left',
                      cursor: 'pointer',
                      fontSize: 'var(--font-size-sm)',
                      color: 'var(--color-text-secondary)',
                      transition: 'background-color 0.2s ease'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--color-bg-secondary)'}
                    onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                  >
                    Sign Out
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
};