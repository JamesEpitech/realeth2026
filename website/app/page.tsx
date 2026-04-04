import Image from "next/image";

export default function Home() {
  const features = [
    {
      icon: "👁",
      title: "Iris Capture",
      description:
        "Guided capture with real-time quality checks and reliable extraction designed for frictionless enrollment.",
    },
    {
      icon: "🛡",
      title: "Anti-Spoofing",
      description:
        "Multi-layer liveness analysis and visual consistency checks that block image, screen, and replay attacks.",
    },
    {
      icon: "🔐",
      title: "Wallet Security",
      description:
        "Wallet-first architecture with secure identity verification, clean handoff, and crypto-ready transaction flows.",
    },
  ];

  const workflow = [
    {
      title: "Capture",
      description: "Align your eye with the guided camera overlay and initiate the scan.",
    },
    {
      title: "Extract",
      description: "A stable biometric fingerprint is derived from the iris pattern.",
    },
    {
      title: "Verify",
      description: "Anti-spoofing checks run before any authentication decision is made.",
    },
    {
      title: "Unlock",
      description: "The wallet experience opens once the identity is cryptographically verified.",
    },
  ];

  const screens = [
    {
      title: "Scan",
      label: "Biometric authentication",
      body: "Position your eye in front of the camera and launch the scan flow. Real-time feedback guides you through alignment.",
      accent: "Live capture",
      chips: ["Camera ready", "Guided overlay"],
    },
    {
      title: "Register",
      label: "Create a new wallet",
      body: "If the iris is unknown, create a wallet and bind it to your unique biometric hash. One identity, one wallet.",
      accent: "Enrollment",
      chips: ["New identity", "Hash binding"],
    },
    {
      title: "Dashboard",
      label: "Wallet connected",
      body: "Once verified, access your balance, wallet address, transaction history, and account status in real time.",
      accent: "Secure session",
      chips: ["Authenticated", "Live data"],
    },
  ];

  const securityItems = [
    "Biometric decision gates before any wallet access",
    "Clear separation between capture, verification, and unlock stages",
    "Compact dashboard-first UI for instant comprehension",
    "Cryptographic hash binding — no raw biometric data stored",
  ];

  return (
    <main>
      {/* ── Topbar ──────────────────────────── */}
      <header className="topbar">
        <div className="topbar-inner">
          <a className="brand" href="#top" aria-label="IrisWallet home">
            <span className="brand-mark">
              <Image src="/logo.png" alt="IrisWallet" width={36} height={36} priority />
            </span>
            <span className="brand-copy">
              <strong>IrisWallet</strong>
              <span>Biometric Wallet</span>
            </span>
          </a>

          <nav className="nav-links" aria-label="Main navigation">
            <a href="#product">Product</a>
            <a href="#workflow">Workflow</a>
            <a href="#screens">Screens</a>
            <a href="#contact" className="nav-cta">Get in touch</a>
          </nav>
        </div>
      </header>

      {/* ── Hero ────────────────────────────── */}
      <section className="hero section-pad" id="top">
        <div className="section-inner hero-grid">
          <div className="hero-copy reveal">
            <p className="eyebrow">Biometric Access</p>
            <h1>
              Your wallet, secured by your iris.
              <span>Fast. Intentional. Unforgeable.</span>
            </h1>
            <p className="lead">
              IrisWallet combines biometric identity, real-time anti-spoofing,
              and secure wallet orchestration into a seamless user experience.
            </p>
            <div className="actions">
              <a href="#workflow" className="btn btn-primary">
                Explore the flow
              </a>
              <a href="#contact" className="btn btn-ghost">
                Talk to us
              </a>
            </div>
            <div className="hero-stats">
              <div className="stat">
                <span className="stat-value">3-step</span>
                <span className="stat-label">Verification</span>
              </div>
              <div className="stat">
                <span className="stat-value">&lt; 2s</span>
                <span className="stat-label">Scan Time</span>
              </div>
              <div className="stat">
                <span className="stat-value">Zero</span>
                <span className="stat-label">Raw Data Stored</span>
              </div>
            </div>
          </div>

          <div className="hero-visual reveal reveal-delay-2">
            <div className="hero-panel">
              <div className="panel-header">
                <div className="panel-header-left">
                  <p>Live Preview</p>
                  <strong>IrisWallet Dashboard</strong>
                </div>
                <span className="status-pill">Connected</span>
              </div>

              <div className="panel-tabs">
                <span className="panel-tab active">Scan</span>
                <span className="panel-tab">Register</span>
                <span className="panel-tab">Dashboard</span>
              </div>

              <div className="scan-area">
                <div className="scan-ring">
                  <div className="scan-core" />
                </div>
                <p className="scan-label">
                  Place your eye in front of the camera and start the biometric scan.
                </p>
                <button className="scan-btn" type="button">
                  <span>👁</span>
                  Scan Iris
                </button>
              </div>

              <div className="panel-info-grid">
                <div className="panel-info-card">
                  <span className="panel-info-label">Balance</span>
                  <span className="panel-info-value">12.48 ETH</span>
                </div>
                <div className="panel-info-card">
                  <span className="panel-info-label">Status</span>
                  <span className="panel-info-value">Verified</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Product ─────────────────────────── */}
      <section id="product" className="section-pad">
        <div className="section-inner">
          <div className="section-head reveal">
            <p className="eyebrow">Product Stack</p>
            <h2>A biometric wallet stack built for trust.</h2>
            <p className="subtitle">
              Every layer is designed to eliminate spoofing, simplify enrollment,
              and keep your digital identity secure.
            </p>
          </div>
          <div className="features-grid">
            {features.map((feature, i) => (
              <article
                key={feature.title}
                className={`feature-card reveal reveal-delay-${i + 1}`}
              >
                <div className="feature-icon">{feature.icon}</div>
                <h3>{feature.title}</h3>
                <p>{feature.description}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* ── Workflow + Security ──────────────── */}
      <section id="workflow" className="section-pad">
        <div className="section-inner">
          <div className="section-head reveal">
            <p className="eyebrow">Workflow</p>
            <h2>From scan to wallet access in four steps.</h2>
          </div>
          <div className="workflow-grid">
            <div className="workflow-steps reveal">
              {workflow.map((step, i) => (
                <div key={step.title} className="step">
                  <span className="step-number">{String(i + 1).padStart(2, "0")}</span>
                  <div className="step-content">
                    <h4>{step.title}</h4>
                    <p>{step.description}</p>
                  </div>
                </div>
              ))}
            </div>

            <div className="security-panel reveal reveal-delay-2" id="security">
              <p className="eyebrow">Security Posture</p>
              <h3>Built to reduce spoofing and keep the flow clean.</h3>
              <ul className="security-list">
                {securityItems.map((item) => (
                  <li key={item} className="security-item">
                    <span className="security-check">✓</span>
                    <p>{item}</p>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* ── App Screens ─────────────────────── */}
      <section id="screens" className="section-pad">
        <div className="section-inner">
          <div className="section-head reveal">
            <p className="eyebrow">App States</p>
            <h2>Three screens that define the experience.</h2>
            <p className="subtitle">
              Each screen maps to a stage in the biometric wallet journey — from
              first scan to full dashboard access.
            </p>
          </div>
          <div className="screens-grid">
            {screens.map((screen, i) => (
              <article
                key={screen.title}
                className={`screen-card reveal reveal-delay-${i + 1}`}
              >
                <div className="screen-top">
                  <span className="screen-badge">{screen.accent}</span>
                  <span className="screen-dot" />
                </div>
                <div className="screen-body">
                  <span className="screen-kicker">{screen.title}</span>
                  <h3>{screen.label}</h3>
                  <p>{screen.body}</p>
                </div>
                <div className="screen-footer">
                  {screen.chips.map((chip) => (
                    <span key={chip} className="screen-chip">{chip}</span>
                  ))}
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA / Contact ───────────────────── */}
      <section id="contact" className="section-pad cta-section">
        <div className="section-inner">
          <div className="cta-card reveal">
            <p className="eyebrow">Contact</p>
            <h2>Ready to build with IrisWallet?</h2>
            <p>
              We are open to technical partnerships, pilot deployments, and
              conversations with teams building the future of secure digital identity.
            </p>
            <div className="actions">
              <a className="btn btn-primary" href="mailto:contact@iriswallet.com">
                contact@iriswallet.com
              </a>
              <a className="btn btn-ghost" href="#top">
                Back to top
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* ── Footer ──────────────────────────── */}
      <footer className="site-footer">
        <div className="section-inner footer-inner">
          <span className="footer-copy">
            &copy; {new Date().getFullYear()} IrisWallet. All rights reserved.
          </span>
          <div className="footer-links">
            <a href="#product">Product</a>
            <a href="#workflow">Workflow</a>
            <a href="#contact">Contact</a>
          </div>
        </div>
      </footer>
    </main>
  );
}
