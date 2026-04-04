import { useState } from 'react';
import { useWallet } from '../context/WalletContext';
import { scanIris } from '../services/api';

export default function ScanScreen() {
  const { setScreen, setWallet, setCurrentHash } = useWallet();
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');

  const handleScan = async () => {
    setLoading(true);
    setError('');
    setStatus('Connexion a la camera...');
    try {
      setStatus('Scan en cours...');
      const result = await scanIris();

      if (result.found) {
        setWallet(result.wallet);
        setScreen('dashboard');
      } else {
        setCurrentHash(result.irisHash);
        setScreen('register');
      }
    } catch (e: any) {
      setError(e.message || 'Impossible de contacter le serveur');
    } finally {
      setLoading(false);
      setStatus('');
    }
  };

  return (
    <div className="screen">
      <div className="logo-section">
        <div className="iris-icon">
          <svg viewBox="0 0 100 100" width="80" height="80">
            <circle cx="50" cy="50" r="45" fill="none" stroke="#00d4ff" strokeWidth="2" />
            <circle cx="50" cy="50" r="30" fill="none" stroke="#00d4ff" strokeWidth="1.5" opacity="0.7" />
            <circle cx="50" cy="50" r="15" fill="none" stroke="#00d4ff" strokeWidth="1" opacity="0.5" />
            <circle cx="50" cy="50" r="8" fill="#00d4ff" opacity="0.3" />
            <circle cx="50" cy="50" r="4" fill="#00d4ff" />
          </svg>
        </div>
        <h1 className="title">IrisWallet</h1>
        <p className="subtitle">Authentification biometrique</p>
      </div>

      <p className="scan-hint">
        Placez votre oeil devant la camera puis appuyez sur le bouton
      </p>

      <button className="btn-primary" onClick={handleScan} disabled={loading}>
        {loading ? (
          <>
            <span className="spinner" />
            {status && <span className="loading-text">{status}</span>}
          </>
        ) : (
          <>
            <span className="btn-icon">👁</span>
            Scanner mon iris
          </>
        )}
      </button>

      {error && <p className="error-msg">{error}</p>}
    </div>
  );
}
