import { useState } from 'react';
import { useWallet } from '../context/WalletContext';
import { register } from '../services/api';
import { createWallet, registerOnChain, getBalance } from '../services/blockchain';
import { formatEther } from 'viem';

export default function RegisterScreen() {
  const { setWallet, setScreen } = useWallet();
  const [walletName, setWalletName] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');

  const handleRegister = async () => {
    if (!walletName.trim()) {
      setError('Veuillez entrer un nom de wallet');
      return;
    }

    setLoading(true);
    setError('');

    try {
      // 1. Generate wallet (stored locally by address)
      const { address } = createWallet();

      // 2. Register in backend with our address
      setStatus('Enregistrement iris...');
      const backendResult = await register(walletName.trim(), address);
      const irisHash = backendResult.wallet?.irisHash || '';

      // 3. Register on-chain
      setStatus('Enregistrement on-chain...');
      const txHash = await registerOnChain(address, irisHash);

      // 4. Get balance
      const bal = await getBalance(address);

      setWallet({
        walletName: walletName.trim(),
        walletAddress: address,
        balance: formatEther(bal),
        createdAt: new Date().toISOString(),
        onChain: true,
        txHash,
      });
      setScreen('dashboard');
    } catch (e: any) {
      setError(e.message || 'Erreur lors de la creation du wallet');
    } finally {
      setLoading(false);
      setStatus('');
    }
  };

  return (
    <div className="screen">
      <div className="logo-section">
        <h1 className="title">Nouveau Wallet</h1>
        <p className="subtitle">Iris detecte — creation du wallet on-chain</p>
      </div>

      <div className="form-group">
        <label className="form-label" htmlFor="wallet-name">Nom du wallet</label>
        <input
          id="wallet-name"
          className="form-input"
          type="text"
          placeholder="Ex: MonWallet"
          value={walletName}
          onChange={(e) => setWalletName(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleRegister()}
        />
      </div>

      <button className="btn-primary" onClick={handleRegister} disabled={loading}>
        {loading ? (
          <>
            <span className="spinner" />
            <span className="loading-text">{status}</span>
          </>
        ) : (
          'Creer mon wallet on-chain'
        )}
      </button>

      {error && <p className="error-msg">{error}</p>}

      <button className="btn-link" onClick={() => setScreen('scan')}>
        ← Retour au scan
      </button>
    </div>
  );
}
