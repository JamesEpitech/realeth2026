import { useState } from 'react';
import { useWallet } from '../context/WalletContext';
import { scanIris } from '../services/api';

const API_URL = 'http://localhost:5000';

export default function ScanScreen() {
  const { setScreen, setWallet, setCurrentHash } = useWallet();
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');

  const handleScan = async () => {
    setLoading(true);
    setError('');
    setStatus('Scan en cours...');
    try {
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
      <div className="logo-section compact">
        <h1 className="title">IrisWallet</h1>
        <p className="subtitle">Authentification biometrique</p>
      </div>

      <div className="camera-container">
        <img
          src={`${API_URL}/api/stream`}
          alt="Camera live"
          className="camera-feed"
        />
        <div className="camera-overlay">
          <div className="camera-reticle" />
        </div>
      </div>

      <p className="scan-hint">
        Placez votre oeil devant la camera
      </p>

      <button className="btn-primary" onClick={handleScan} disabled={loading}>
        {loading ? (
          <>
            <span className="spinner" />
            <span className="loading-text">{status}</span>
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
