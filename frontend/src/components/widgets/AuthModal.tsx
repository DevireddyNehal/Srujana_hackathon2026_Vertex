import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import type { UserProfile } from "../../types/trading";
import { getDemoUsers, switchDemoUser, loginUser, registerUser } from "../../api/client";

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentUser: UserProfile | null;
  onUserChanged: (user: UserProfile, token: string) => void;
}

export function AuthModal({ isOpen, onClose, currentUser, onUserChanged }: AuthModalProps) {
  const [activeTab, setActiveTab] = useState<"demo" | "login" | "register">("demo");
  const [demoUsers, setDemoUsers] = useState<UserProfile[]>([]);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Login form state
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");

  // Register form state
  const [regName, setRegName] = useState("");
  const [regEmail, setRegEmail] = useState("");
  const [regPassword, setRegPassword] = useState("");
  const [regBalance, setRegBalance] = useState("50000");
  const [regCurrency, setRegCurrency] = useState("USD");
  const [regTimezone, setRegTimezone] = useState("America/New_York");

  useEffect(() => {
    if (isOpen) {
      loadDemoUsers();
      setErrorMsg(null);
      setSuccessMsg(null);
    }
  }, [isOpen]);

  async function loadDemoUsers() {
    try {
      setLoading(true);
      const users = await getDemoUsers();
      setDemoUsers(users);
    } catch (err) {
      console.error("Failed to load demo users:", err);
    } finally {
      setLoading(false);
    }
  }

  async function handleSwitchDemo(userId: string) {
    try {
      setLoading(true);
      setErrorMsg(null);
      const res = await switchDemoUser(userId);
      const targetUser = demoUsers.find((u) => u.id === res.active_user_id) || {
        id: res.active_user_id,
        name: res.user_name,
        email: `${res.active_user_id}@demo.test`,
        starting_balance: 50000,
        currency: "USD",
        timezone: "UTC",
        is_demo: true,
        created_at: new Date().toISOString(),
      };
      localStorage.setItem("vertex_active_user_id", res.active_user_id);
      localStorage.setItem("vertex_auth_token", res.token);
      onUserChanged(targetUser, res.token);
      setSuccessMsg(`Switched to ${res.user_name}!`);
      setTimeout(() => {
        onClose();
      }, 600);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to switch demo trader");
    } finally {
      setLoading(false);
    }
  }

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    try {
      setLoading(true);
      setErrorMsg(null);
      const res = await loginUser({ email: loginEmail, password: loginPassword });
      localStorage.setItem("vertex_active_user_id", res.user.id);
      localStorage.setItem("vertex_auth_token", res.token);
      onUserChanged(res.user, res.token);
      setSuccessMsg(`Logged in as ${res.user.name}!`);
      setTimeout(() => {
        onClose();
      }, 600);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Invalid credentials");
    } finally {
      setLoading(false);
    }
  }

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault();
    try {
      setLoading(true);
      setErrorMsg(null);
      const res = await registerUser({
        name: regName,
        email: regEmail,
        password: regPassword,
        starting_balance: parseFloat(regBalance) || 50000,
        currency: regCurrency,
        timezone: regTimezone,
      });
      localStorage.setItem("vertex_active_user_id", res.user.id);
      localStorage.setItem("vertex_auth_token", res.token);
      onUserChanged(res.user, res.token);
      setSuccessMsg(`Account created for ${res.user.name}!`);
      setTimeout(() => {
        onClose();
      }, 600);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  if (!isOpen) return null;

  return createPortal(
    <div className="auth-modal-backdrop" onClick={onClose}>
      <div className="auth-modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="auth-modal-header">
          <div className="auth-title-wrap">
            <span className="auth-icon">🔐</span>
            <div>
              <h3>Trader Authentication & Multi-User Switcher</h3>
              <p className="auth-subtitle">
                Isolated trade data, journal, and stats per user account
              </p>
            </div>
          </div>
          <button className="auth-close-btn" onClick={onClose} title="Close">
            ✕
          </button>
        </div>

        {currentUser && (
          <div className="current-user-banner">
            <span className="badge-dot"></span>
            <span>Active Session: <strong>{currentUser.name}</strong> ({currentUser.currency} ${currentUser.starting_balance.toLocaleString()})</span>
            {currentUser.is_demo && <span className="demo-pill">DEMO DATASET</span>}
          </div>
        )}

        {errorMsg && <div className="auth-alert error-alert">{errorMsg}</div>}
        {successMsg && <div className="auth-alert success-alert">{successMsg}</div>}

        <div className="auth-tabs">
          <button
            className={`auth-tab-btn ${activeTab === "demo" ? "active" : ""}`}
            onClick={() => setActiveTab("demo")}
          >
            👥 10 Demo Traders
          </button>
          <button
            className={`auth-tab-btn ${activeTab === "login" ? "active" : ""}`}
            onClick={() => setActiveTab("login")}
          >
            🔑 Account Login
          </button>
          <button
            className={`auth-tab-btn ${activeTab === "register" ? "active" : ""}`}
            onClick={() => setActiveTab("register")}
          >
            ✨ Register New User
          </button>
        </div>

        <div className="auth-tab-body">
          {activeTab === "demo" && (
            <div className="demo-traders-list">
              <p className="tab-desc">
                Switch instantaneously between 10 seeded trading personas. Each trader features 10,000 isolated trades with distinct strategies and performance footprints.
              </p>
              <div className="demo-grid">
                {demoUsers.map((user) => (
                  <div
                    key={user.id}
                    className={`demo-card ${currentUser?.id === user.id ? "selected" : ""}`}
                  >
                    <div className="demo-card-head">
                      <strong>{user.name}</strong>
                      <span className="demo-balance">${user.starting_balance.toLocaleString()} {user.currency}</span>
                    </div>
                    <div className="demo-desc">{user.profile_description || "Algorithmic trader"}</div>
                    <div className="demo-meta">
                      <span>🌍 {user.timezone}</span>
                    </div>
                    <button
                      className="btn-select-demo"
                      disabled={loading || currentUser?.id === user.id}
                      onClick={() => handleSwitchDemo(user.id)}
                    >
                      {currentUser?.id === user.id ? "✓ Active Trader" : "Switch Trader"}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === "login" && (
            <form onSubmit={handleLogin} className="auth-form">
              <p className="tab-desc">
                Sign in to your private trading account. Data is strictly isolated.
              </p>
              <div className="form-group">
                <label>Email Address</label>
                <input
                  type="email"
                  required
                  placeholder="e.g. demo.trader01@tradefxbook.demo"
                  value={loginEmail}
                  onChange={(e) => setLoginEmail(e.target.value)}
                  className="auth-input"
                />
              </div>
              <div className="form-group">
                <label>Password</label>
                <input
                  type="password"
                  required
                  placeholder="Password"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  className="auth-input"
                />
                <span className="input-hint">Demo accounts use password: <code>demo123</code></span>
              </div>
              <button type="submit" disabled={loading} className="btn-auth-submit">
                {loading ? "Authenticating..." : "Sign In"}
              </button>
            </form>
          )}

          {activeTab === "register" && (
            <form onSubmit={handleRegister} className="auth-form">
              <p className="tab-desc">
                Create a fresh, isolated trading account with custom starting capital.
              </p>
              <div className="form-row">
                <div className="form-group">
                  <label>Full Name</label>
                  <input
                    type="text"
                    required
                    placeholder="Trader Name"
                    value={regName}
                    onChange={(e) => setRegName(e.target.value)}
                    className="auth-input"
                  />
                </div>
                <div className="form-group">
                  <label>Email Address</label>
                  <input
                    type="email"
                    required
                    placeholder="trader@vertex.finance"
                    value={regEmail}
                    onChange={(e) => setRegEmail(e.target.value)}
                    className="auth-input"
                  />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Password</label>
                  <input
                    type="password"
                    required
                    minLength={4}
                    placeholder="At least 4 characters"
                    value={regPassword}
                    onChange={(e) => setRegPassword(e.target.value)}
                    className="auth-input"
                  />
                </div>
                <div className="form-group">
                  <label>Starting Balance</label>
                  <input
                    type="number"
                    required
                    min={100}
                    value={regBalance}
                    onChange={(e) => setRegBalance(e.target.value)}
                    className="auth-input"
                  />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Account Currency</label>
                  <select
                    value={regCurrency}
                    onChange={(e) => setRegCurrency(e.target.value)}
                    className="auth-input"
                  >
                    <option value="USD">USD ($)</option>
                    <option value="INR">INR (₹)</option>
                    <option value="EUR">EUR (€)</option>
                    <option value="GBP">GBP (£)</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Timezone</label>
                  <select
                    value={regTimezone}
                    onChange={(e) => setRegTimezone(e.target.value)}
                    className="auth-input"
                  >
                    <option value="America/New_York">America/New_York (EST/EDT)</option>
                    <option value="Europe/London">Europe/London (GMT/BST)</option>
                    <option value="Asia/Kolkata">Asia/Kolkata (IST)</option>
                    <option value="Asia/Tokyo">Asia/Tokyo (JST)</option>
                    <option value="UTC">UTC</option>
                  </select>
                </div>
              </div>
              <button type="submit" disabled={loading} className="btn-auth-submit">
                {loading ? "Creating Account..." : "Create Account & Start Journaling"}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
}
