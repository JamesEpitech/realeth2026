import { useEffect, useState, useRef } from 'react';
import { useWallet } from '../context/WalletContext';
import { getBalance } from '../services/blockchain';
import { formatEther, type Address } from 'viem';

const API_URL = 'http://localhost:5000';

export default function ScanScreen() {
  const { setScreen, setWallet } = useWallet();
  const [status, setStatus] = useState('Recherche de votre oeil...');
  const [error, setError] = useState('');
  const [unknown, setUnknown] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  const startAutoScan = () => {
    setError('');
    setUnknown(false);
    setStatus('Recherche de votre oeil...');

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      fetch(`${API_URL}/api/autoscan/stop`, { method: 'POST' }).catch(() => {});
    }

    const es = new EventSource(`${API_URL}/api/autoscan`);
    eventSourceRef.current = es;

    es.onmessage = async (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.status === 'scanning') {
          setStatus('Recherche de votre iris...');
          return;
        }

        es.close();
        eventSourceRef.current = null;

        if (data.status === 'found') {
          // Backend matched iris — the wallet address is the one we gave at register
          const address = data.wallet?.address || data.wallet?.walletAddress;
          const name = data.wallet?.walletName || 'IrisWallet';
          const created = data.wallet?.createdAt || new Date().toISOString();

          // Fetch real balance from chain
          let balance = '0';
          try {
            const bal = await getBalance(address as Address);
            balance = formatEther(bal);
          } catch { /* ignore */ }

          setWallet({
            walletName: name,
            walletAddress: address,
            balance,
            createdAt: created,
            onChain: true,
          });
          setScreen('dashboard');
        } else if (data.status === 'unknown') {
          setUnknown(true);
          setStatus('Iris non reconnu');
        }
      } catch { /* ignore */ }
    };

    es.onerror = () => {
      setError('Connexion au serveur perdue');
      es.close();
      eventSourceRef.current = null;
    };
  };

  useEffect(() => {
    startAutoScan();
    return () => {
      if (eventSourceRef.current) eventSourceRef.current.close();
      fetch(`${API_URL}/api/autoscan/stop`, { method: 'POST' }).catch(() => {});
    };
  }, []);

  return (
    <div className="screen">
      <div className="logo-section compact">
        <h1 className="title">IrisWallet</h1>
        <p className="subtitle">Authentification biometrique on-chain</p>
      </div>

      <div className="camera-container">
        <img src={`${API_URL}/api/stream`} alt="Camera live" className="camera-feed" />
        <div className="camera-overlay">
          <div className={`camera-reticle ${unknown ? 'reticle-warning' : ''}`} />
        </div>
      </div>

      {error ? (
        <p className="error-msg">{error}</p>
      ) : unknown ? (
        <>
          <p className="scan-status warning">Iris non reconnu — aucun compte associe</p>
          <button className="btn-primary" onClick={() => setScreen('register')}>Creer un compte</button>
          <button className="btn-link" onClick={() => { setUnknown(false); startAutoScan(); }}>Reessayer le scan</button>
        </>
      ) : (
        <>
          <div className="scan-status">
            <span className="scan-status-dot" />
            <span>{status}</span>
          </div>
          <p className="scan-hint">Placez votre oeil devant la camera, le scan est automatique</p>
        </>
      )}
    </div>
  );
}
