const API_URL = 'http://localhost:5000';

export async function scanIris() {
  // Demande au backend de capturer une photo via le Pi
  // et de lancer la pipeline iris recognition
  const res = await fetch(`${API_URL}/api/scan`, {
    method: 'POST',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || 'Erreur lors du scan');
  }
  return res.json();
}

export async function register(walletName: string) {
  // Le backend re-capture une frame et cree le compte
  const res = await fetch(`${API_URL}/api/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ walletName }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || "Erreur lors de l'enregistrement");
  }
  return res.json();
}
