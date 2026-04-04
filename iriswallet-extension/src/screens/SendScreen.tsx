import { useState, useRef } from 'react';
import { useWallet } from '../context/WalletContext';
import { sendTransaction, getBalance } from '../services/blockchain';
import { formatEther, type Address } from 'viem';

const API_URL = 'http://localhost:5000';

type Step = 'form' | 'signing' | 'success';

export default function SendScreen() {
  const { wallet, setWallet, setScreen } = useWallet();
  const [to, setTo] = useState('0x3656Ff4C11C4C8b4b77402fAab8B3387E36f2e77');
  const [amount, setAmount] = useState('0.0001');
  const [step, setStep] = useState<Step>('form');
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [txHash, setTxHash] = useState('');
  const eventSourceRef = useRef<EventSource | null>(null);

  if (!wallet) return null;

  const startIrisScan = () => {
    if (!to.trim() || !to.startsWith('0x')) { setError('Adresse invalide'); return; }
    if (!parseFloat(amount) || parseFloat(amount) <= 0) { setError('Montant invalide'); return; }

    setError('');
    setStep('signing');
    setStatus('Placez votre oeil devant la camera...');

    const es = new EventSource(`${API_URL}/api/autoscan`);
    eventSourceRef.current = es;

    es.onmessage = async (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.status === 'scanning') { setStatus('Recherche de votre iris...'); return; }

        es.close();
        eventSourceRef.current = null;

        if (data.status !== 'found') {
          setError('Iris non reconnu — transaction refusee');
          setStep('form');
          return;
        }

        // Backend verified iris via Hamming distance — send tx
        setStatus('Iris verifie — envoi en cours...');
        try {
          const hash = await sendTransaction(
            wallet.walletAddress as Address,
            to.trim() as Address,
            amount,
          );
          setTxHash(hash);
          setStep('success');

          const bal = await getBalance(wallet.walletAddress as Address);
          setWallet({ ...wallet, balance: formatEther(bal) });
        } catch (e: any) {
          setError(e.message?.includes('insufficient') ? 'Solde insuffisant' : (e.message || 'Erreur envoi'));
          setStep('form');
        }
      } catch { /* ignore */ }
    };

    es.onerror = () => {
      setError('Connexion au serveur perdue');
      es.close();
      eventSourceRef.current = null;
      setStep('form');
    };
  };

  const cancelScan = () => {
    if (eventSourceRef.current) eventSourceRef.current.close();
    fetch(`${API_URL}/api/autoscan/stop`, { method: 'POST' }).catch(() => {});
    setStep('form');
  };

  return (
    <div className="screen">
      <div className="logo-section">
        <h1 className="title">Envoyer ETH</h1>
        <p className="subtitle">{step === 'signing' ? 'Scan iris pour autoriser' : 'Un scan iris est requis pour signer'}</p>
      </div>

      {step === 'success' ? (
        <div className="dashboard-card">
          <p className="scan-status success">Transaction confirmee</p>
          <div className="info-row">
            <span className="info-label">Tx</span>
            <a className="info-value mono" href={`https://sepolia.etherscan.io/tx/${txHash}`} target="_blank" rel="noopener noreferrer">
              {txHash.slice(0, 10)}...{txHash.slice(-4)}
            </a>
          </div>
          <div className="info-row">
            <span className="info-label">Montant</span>
            <span className="info-value">{amount} ETH</span>
          </div>
          <button className="btn-primary" onClick={() => setScreen('dashboard')}>Retour au dashboard</button>
        </div>
      ) : (
        <>
          <div className="camera-container">
            <img src={`${API_URL}/api/stream`} alt="Camera live" className="camera-feed" />
            <div className="camera-overlay">
              <div className={`camera-reticle ${step === 'signing' ? 'reticle-scanning' : ''}`} />
            </div>
          </div>

          {step === 'form' && (
            <>
              <div className="form-group">
                <label className="form-label" htmlFor="send-to">Adresse destinataire</label>
                <input id="send-to" className="form-input" type="text" placeholder="0x..." value={to} onChange={(e) => setTo(e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor="send-amount">
                  Montant (ETH)
                  <span className="balance-hint"> — dispo: {parseFloat(String(wallet.balance)).toFixed(4)}</span>
                </label>
                <input id="send-amount" className="form-input" type="number" step="0.0001" placeholder="0.001" value={amount} onChange={(e) => setAmount(e.target.value)} />
              </div>
              <button className="btn-primary" onClick={startIrisScan}>Signer avec mon iris</button>
              {error && <p className="error-msg">{error}</p>}
              <button className="btn-link" onClick={() => setScreen('dashboard')}>← Retour</button>
            </>
          )}

          {step === 'signing' && (
            <>
              <div className="scan-status"><span className="scan-status-dot" /><span>{status}</span></div>
              <p className="scan-hint">Le scan est automatique — gardez votre oeil devant la camera</p>
              <button className="btn-link" onClick={cancelScan}>Annuler</button>
            </>
          )}
        </>
      )}
    </div>
  );
}
