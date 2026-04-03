# IRISWALLET

**Iris-Authenticated Blockchain Wallet**

**Audit Complet du Projet & Répartition des Tâches**

**ETHGlobal Cannes 2026**

*Avril 2026 — Document Confidentiel*

*Équipe : 4 développeurs | Durée : 36h de hackathon*

*Partenaires : World · Ledger · Chainlink*

---

## 1. Executive Summary

IrisWallet est un système d'authentification biométrique par scan d'iris qui permet de créer, déverrouiller et sécuriser un wallet blockchain. Chaque iris étant unique, il sert de clé biométrique irrévocable liée à un wallet on-chain.

Le projet se compose de trois couches : un hardware (Raspberry Pi + caméra IR) qui capture l'iris, une extension Chrome qui gère le wallet et intercepte les transactions, et un ensemble de smart contracts qui valident l'identité on-chain via World ID 4.0, sécurisent la signature via Ledger, et protègent les données biométriques via Chainlink Confidential Compute.

### 1.1 Problème résolu

Les wallets crypto reposent sur des seed phrases (12-24 mots) que les utilisateurs perdent, se font voler, ou oublient. Les solutions actuelles (hardware wallets, MPC) restent complexes. IrisWallet remplace la seed phrase par quelque chose que l'utilisateur ne peut ni perdre ni oublier : son iris.

### 1.2 Proposition de valeur

- **Zéro seed phrase à retenir** — votre iris EST votre clé privée
- **Impossibilité de vol** — l'iris ne peut pas être copié ou phishé comme un mot de passe
- **Vérification d'unicité humaine** via World ID 4.0 (anti-sybil)
- **Données biométriques jamais exposées on-chain** (Chainlink Confidential Compute)
- **Approbation hardware** de chaque transaction critique (Ledger trust layer)

---

## 2. Architecture Technique Détaillée

### 2.1 Vue d'ensemble de l'architecture

L'architecture se décompose en 4 couches principales :

| Couche | Composant | Technologie | Rôle |
|--------|-----------|-------------|------|
| Hardware | Raspberry Pi 4/5 + Caméra IR | Python, OpenCV, Flask API | Capture de l'iris, pré-traitement de l'image, extraction du template biométrique |
| Client | Extension Chrome (Manifest V3) | TypeScript, React, Viem | Interface utilisateur, gestion du wallet, interception des transactions dApp |
| Backend | Serveur API | Node.js / Express | Validation des preuves World ID, orchestration, stockage chiffré des templates |
| Blockchain | Smart Contracts | Solidity (World Chain) | Vérification on-chain de World ID, binding iris-wallet, logique d'approbation |
| Oracle | Chainlink CRE Workflow | TypeScript SDK | Confidential HTTP pour le matching biométrique off-chain sécurisé |

### 2.2 Flow d'Enrollment (Première utilisation)

Voici le parcours complet lors de la première inscription d'un utilisateur :

1. **Étape 1 — Scan physique** : L'utilisateur place son œil devant la caméra IR branchée au Raspberry Pi. Le Pi capture une image haute résolution de l'iris en proche infrarouge.
2. **Étape 2 — Extraction du template** : Le Raspberry Pi exécute un algorithme de segmentation d'iris (détection pupille/iris via Hough Transform + Daugman's integrodifferential operator), puis encode l'iris en un template binaire (IrisCode) de 2048 bits.
3. **Étape 3 — Vérification World ID** : L'extension Chrome déclenche une vérification World ID 4.0 via IDKit. L'utilisateur prouve son unicité humaine. La preuve (nullifier hash) est générée.
4. **Étape 4 — Création du wallet** : L'extension génère une paire de clés (clé privée + adresse publique). La clé privée est chiffrée avec le hash du template iris comme clé de chiffrement (AES-256-GCM).
5. **Étape 5 — Binding on-chain** : Un smart contract sur World Chain enregistre le lien entre le nullifier World ID et l'adresse du wallet. Cela garantit : un iris = un wallet, vérifiable publiquement.
6. **Étape 6 — Stockage sécurisé** : Le template iris chiffré est stocké localement dans l'extension (chrome.storage.local) et un backup chiffré peut être stocké côté backend. La clé privée n'existe jamais en clair en dehors de la mémoire volatile.

### 2.3 Flow de Transaction (Utilisation courante)

1. **Étape 1 — Détection** : L'extension Chrome détecte qu'un dApp demande une signature (injection du provider web3).
2. **Étape 2 — Popup d'approbation** : L'extension affiche les détails de la transaction et demande un scan d'iris pour approuver.
3. **Étape 3 — Re-scan** : L'utilisateur scanne son iris via le Raspberry Pi. Le nouveau template est comparé au template stocké via Chainlink Confidential HTTP (matching off-chain, zéro donnée biométrique on-chain).
4. **Étape 4 — Signature Ledger** : Si le match est positif (Hamming distance < seuil), la transaction est signée via le Ledger DMK (Device Management Kit) comme couche de confiance supplémentaire.
5. **Étape 5 — Broadcast** : La transaction signée est envoyée au réseau blockchain.

### 2.4 Sécurité & Privacy Architecture

La sécurité des données biométriques est la priorité absolue du projet. Voici les mécanismes :

**Données biométriques**

- Le template iris (IrisCode) n'est jamais stocké en clair — toujours chiffré AES-256-GCM
- Le matching (comparaison entre deux templates) se fait exclusivement via Chainlink Confidential HTTP dans un environnement TEE (Trusted Execution Environment)
- Aucune donnée biométrique ne touche jamais la blockchain — seul un booléen (match/no-match) est retourné on-chain
- L'image brute de l'iris est supprimée immédiatement après l'extraction du template sur le Raspberry Pi

**Clés privées**

- La clé privée du wallet est chiffrée avec le hash du template iris — elle ne peut être déchiffrée qu'avec un scan iris valide
- En mémoire volatile uniquement pendant la signature, puis wipe immédiat
- La couche Ledger DMK ajoute une vérification hardware indépendante

**Anti-Spoofing**

- Détection de vivacité (liveness detection) via la caméra IR : analyse de la réflexion pupillaire, micro-mouvements oculaires
- World ID 4.0 comme couche anti-sybil — impossible de créer plusieurs wallets avec le même iris

---

## 3. Stack Technique Détaillée

### 3.1 Hardware — Raspberry Pi + Caméra IR

| Composant | Spécification | Justification |
|-----------|---------------|---------------|
| Raspberry Pi | Model 4B (4GB RAM) ou 5 | Suffisant pour le traitement d'image, GPIO pour la caméra, WiFi intégré |
| Caméra | Module caméra Pi NoIR v2 + filtre IR-pass | Capture en proche infrarouge pour un contraste iris optimal |
| LED IR | Array de LEDs 850nm | Éclairage IR pour illuminer l'iris sans gêner l'utilisateur |
| Boitier | Impression 3D ou proto carton | Positionnement fixe de l'œil à distance focale optimale |
| Connectivité | WiFi ou USB-Ethernet | Communication avec l'extension Chrome via API REST locale |

### 3.2 Software Raspberry Pi

| Librairie / Outil | Version | Usage |
|--------------------|---------|-------|
| Python | 3.11+ | Langage principal du traitement d'image |
| OpenCV | 4.9+ | Capture vidéo, détection cercles (Hough Transform), pré-traitement |
| NumPy | 1.26+ | Manipulation de matrices pour l'IrisCode |
| Flask | 3.0+ | API REST locale (serveur HTTP sur le Pi) |
| open-iris ou custom | Latest | Segmentation iris + encodage IrisCode (Gabor filters) |
| cryptography | 42+ | Chiffrement AES-256-GCM du template avant envoi |

### 3.3 Extension Chrome

| Technologie | Version | Usage |
|-------------|---------|-------|
| Manifest V3 | Chrome 120+ | Architecture de l'extension (service worker, content scripts) |
| TypeScript | 5.4+ | Langage principal — typage fort pour la sécurité |
| React | 18+ | UI des popups et pages de l'extension |
| Viem | 2.x | Client Ethereum : interactions blockchain, encodage ABI |
| @worldcoin/idkit | Latest | Intégration World ID 4.0 dans l'extension |
| @ledgerhq/device-management-kit | Latest | Ledger DMK pour la signature sécurisée |
| Web Crypto API | Native | Chiffrement/déchiffrement AES-256-GCM côté client |
| Webpack / Vite | Latest | Bundling de l'extension |

### 3.4 Backend

| Technologie | Usage |
|-------------|-------|
| Node.js + Express | Serveur API pour la validation des preuves World ID |
| @worldcoin/idkit-core | Vérification backend des preuves ZKP World ID |
| Chainlink CRE SDK (TypeScript) | Construction et simulation des CRE Workflows |
| Chainlink CRE CLI | Compilation, simulation et déploiement des workflows |
| ethers.js v6 | Interactions smart contract côté backend |
| Redis (optionnel) | Cache des sessions de vérification, rate limiting |

### 3.5 Smart Contracts (Solidity)

| Contrat | Chain | Fonction |
|---------|-------|----------|
| IrisRegistry.sol | World Chain | Enregistre le binding World ID nullifier <-> adresse wallet. Empêche la création de doublons (un iris = un wallet). |
| IrisVerifier.sol | World Chain | Reçoit le résultat du matching Chainlink (booléen) et autorise ou bloque la transaction. |
| WorldIDVerifier.sol | World Chain | Vérifie les preuves ZKP World ID 4.0 on-chain via le contrat World ID Router. |

### 3.6 Landing Page

| Technologie | Usage |
|-------------|-------|
| Next.js 14+ (App Router) | Framework React SSR pour la landing page |
| Tailwind CSS | Styling rapide et responsive |
| Framer Motion | Animations fluides pour la démo |
| Vercel | Hébergement et déploiement instantané |

---

## 4. Intégration Partenaires — Stratégie Détaillée

### 4.1 World — World ID 4.0 (Track: Best use of World ID 4.0 — $8,000)

**Ce qu'on utilise**

- **IDKit SDK** : intégré dans l'extension Chrome pour déclencher la vérification World ID
- **World ID 4.0 Protocol** : preuve d'unicité humaine (Proof of Personhood)
- **On-chain verification** : validation des preuves ZKP dans un smart contract sur World Chain

**Comment on remplit les critères**

- **World ID comme contrainte réelle** : sans World ID validé, impossible de créer un wallet. C'est un gate obligatoire, pas un bonus.
- **Unicité** : le nullifier hash de World ID est lié 1:1 au wallet dans le smart contract IrisRegistry.sol
- **Proof validation on-chain** : le contrat WorldIDVerifier.sol vérifie la preuve ZKP via le World ID Router déployé sur World Chain
- **Rate limiting naturel** : un humain = un iris = un wallet = impossible de spam

**Implémentation technique**

Dans l'extension Chrome, lors de l'enrollment :

- Appel `IDKit.verify()` avec `action = 'create-iris-wallet'` et `signal = hash du template iris`
- L'utilisateur vérifie son identité via World App
- La preuve (`merkle_root`, `nullifier_hash`, `proof`) est récupérée
- Le backend valide la preuve via l'API World ID, puis la soumet au smart contract
- Le smart contract vérifie on-chain et enregistre le binding `nullifier <-> wallet address`

### 4.2 Ledger — Trust Layer (Track: AI Agents x Ledger — $6,000)

**Ce qu'on utilise**

- **Ledger Device Management Kit (DMK)** : SDK JavaScript pour interagir avec les devices Ledger
- **Human-in-the-loop approval** : le scan d'iris + Ledger forment une double vérification
- **Clear Signing concepts** : affichage clair de ce que l'utilisateur signe

**Comment on remplit les critères**

- **Ledger comme trust layer pour l'authentification** : le scan d'iris déclenche l'approbation, Ledger signe la transaction de manière sécurisée
- **Human-in-the-loop** : Ledger empêche toute transaction sans approbation physique humaine (iris scan + confirmation Ledger)
- **Copilot concept** : l'extension explique chaque transaction avant signature, simule les résultats, et affiche les risques

**Implémentation technique**

- L'extension intègre `@ledgerhq/device-management-kit` pour détecter et communiquer avec un Ledger connecté (USB/Bluetooth)
- Après un match iris positif, la transaction est envoyée au Ledger pour signature finale
- Si pas de Ledger physique : le DMK peut fonctionner en mode software comme couche de sécurité additionnelle
- Génération de Clear Signing JSON pour que le Ledger affiche les détails humainement lisibles de la transaction

### 4.3 Chainlink — Confidential Compute (Track: Privacy Standard — $2,000)

**Ce qu'on utilise**

- **Chainlink CRE (Runtime Environment)** : orchestration du workflow de vérification biométrique
- **Confidential HTTP** : appels API sécurisés où les données (template iris) ne sont jamais exposées
- **CRE SDK TypeScript** : construction du workflow
- **CRE CLI** : simulation et déploiement

**Le Workflow CRE**

Le workflow CRE orchestre le matching biométrique de manière entièrement privée :

1. **Trigger** : l'extension envoie le template iris chiffré au CRE workflow via Confidential HTTP
2. **Fetch** : le workflow récupère le template de référence stocké (via Confidential HTTP — credentials protégés)
3. **Compute** : comparaison des deux templates (Hamming distance) dans l'environnement CRE sécurisé — les données ne quittent jamais le TEE
4. **Result** : retour d'un booléen (match/no-match) + score de confiance, signé par le DON
5. **On-chain** : le résultat est envoyé au smart contract IrisVerifier.sol qui autorise ou bloque la transaction

**Ce que ça protège**

- Le template iris n'est jamais visible on-chain ni par aucun noeud individuel
- Les credentials API pour accéder au backend de stockage des templates sont protégés
- La logique de matching est exécutée off-chain dans un TEE, seul le résultat est publié

---

## 5. Répartition des Tâches — 4 Personnes

L'équipe est divisée en 4 rôles spécialisés avec des points de synchronisation clés. Chaque membre a un domaine principal mais contribue aux interfaces entre composants.

### 5.1 Personne 1 — «Hardware & Vision» (Raspberry Pi + Iris Processing)

**Rôle** : Responsable de toute la chaîne hardware, de la capture d'image au template iris prêt à être envoyé.

**Tâches détaillées**

- **T1.1 — Setup Raspberry Pi (2h)** : Installation de Raspberry Pi OS Lite, configuration WiFi, installation de Python 3.11+, OpenCV, NumPy, Flask. Test de la caméra (raspistill / libcamera-still). Configuration des LEDs IR via GPIO.
- **T1.2 — Capture d'image (3h)** : Script Python de capture vidéo en temps réel via la caméra NoIR. Détection automatique de l'œil dans le flux vidéo (Haar Cascade ou DNN). Guidage utilisateur (cadrage, distance, éclairage). Capture de l'image optimale avec score de qualité.
- **T1.3 — Segmentation iris (4h)** : Implémentation de la détection des contours iris/pupille (Hough Transform circulaire). Normalisation de l'iris (unwrapping en coordonnées polaires — Daugman's rubber sheet model). Gestion des occlusions (paupières, cils) via masque binaire.
- **T1.4 — Encodage IrisCode (3h)** : Application de filtres de Gabor 2D multi-échelle sur l'iris normalisé. Génération du template binaire (IrisCode) de 2048 bits. Implémentation de la Hamming distance pour le matching. Tests avec différents yeux pour calibrer le seuil (généralement HD < 0.32 = match).
- **T1.5 — API REST locale (2h)** : Serveur Flask exposant les endpoints : `POST /scan` (déclenche un scan et retourne le template chiffré), `POST /match` (compare deux templates, retourne le score), `GET /status` (vérifie que le hardware est connecté). Chiffrement AES-256-GCM du template avant envoi. CORS configuré pour l'extension Chrome uniquement.
- **T1.6 — Anti-spoofing basique (2h)** : Détection de vivacité : vérification de la réflexion spéculaire de la cornée, détection de micro-mouvements pupillaires, rejet des images imprimées ou écrans (analyse de texture IR).
- **T1.7 — Démo physique (2h)** : Assemblage propre du prototype (caméra + LEDs + Pi dans un support). Script de démo automatisé pour le jury. Tests de robustesse (différentes conditions de lumière, différents utilisateurs).

**Livrables**

- Prototype hardware fonctionnel (Raspberry Pi + caméra + LEDs)
- API REST locale documentée (Swagger/OpenAPI)
- Script de démo end-to-end (scan → template → matching)
- Seuil de matching calibré avec au moins 4 iris différents (l'équipe)

**Dépendances**

- *Reçoit* : spécification du format de template attendu par l'extension (Personne 2)
- *Fournit* : API REST fonctionnelle pour l'extension (Personne 2) et le backend (Personne 3)

### 5.2 Personne 2 — «Frontend & Extension Chrome»

**Rôle** : Responsable de l'extension Chrome (cœur du produit) et de la landing page.

**Tâches détaillées**

- **T2.1 — Scaffold Extension Chrome (2h)** : Setup du projet TypeScript + React + Vite pour Manifest V3. Structure : background service worker, content script (injection provider), popup UI, options page. Configuration de Webpack/Vite pour le bundling multi-entry.
- **T2.2 — Web3 Provider Injection (3h)** : Content script qui injecte un provider EIP-1193 compatible dans chaque page. Interception de `eth_sendTransaction`, `eth_signTypedData`, `personal_sign`. Redirection vers le popup de l'extension pour approbation. Compatibilité avec les dApps existantes (Uniswap, OpenSea, etc.).
- **T2.3 — UI d'Enrollment (3h)** : Flow d'onboarding en 4 étapes : (1) Bienvenue + explication, (2) Connexion au Raspberry Pi (découverte réseau local), (3) Scan iris avec feedback visuel en temps réel, (4) Vérification World ID via IDKit. Design soigné avec animations (Framer Motion). Gestion des erreurs (caméra non détectée, scan échoué, World ID refusé).
- **T2.4 — UI de Transaction (3h)** : Popup d'approbation : affichage des détails de la transaction (destinataire, montant, gas, risques), bouton 'Scan Iris to Approve', animation pendant le scan, confirmation ou rejet. Intégration du Clear Signing (détails humainement lisibles de la transaction). Historique des transactions dans l'extension.
- **T2.5 — Intégration World IDKit (2h)** : Installation et configuration de `@worldcoin/idkit` dans l'extension. Appel `IDKit.verify()` lors de l'enrollment. Stockage sécurisé du nullifier hash et de la preuve. Envoi de la preuve au backend pour validation.
- **T2.6 — Intégration Ledger DMK (2h)** : Installation de `@ledgerhq/device-management-kit`. Détection automatique du Ledger connecté (USB). Envoi de la transaction au Ledger pour signature. Gestion du cas 'pas de Ledger' (mode software fallback).
- **T2.7 — Communication avec le Pi (2h)** : Client HTTP dans l'extension pour appeler l'API du Raspberry Pi. Découverte automatique du Pi sur le réseau local (mDNS / hardcoded IP pour la démo). WebSocket optionnel pour le feedback en temps réel du scan. Gestion du timeout et retry.
- **T2.8 — Gestion du Wallet (2h)** : Génération de la paire de clés via Web Crypto API. Chiffrement de la clé privée avec le hash du template iris (AES-256-GCM). Stockage dans `chrome.storage.local`. Dérivation d'adresse Ethereum. Affichage du solde et des tokens.
- **T2.9 — Landing Page (3h)** : Next.js + Tailwind CSS. Sections : Hero avec animation iris, Explication du fonctionnement (3 étapes visuelles), Architecture technique (diagramme interactif), Partenaires (World, Ledger, Chainlink), CTA 'Install Extension'. Déploiement Vercel. Responsive (mobile + desktop).

**Livrables**

- Extension Chrome fonctionnelle installée localement (mode développeur)
- Landing page déployée sur Vercel
- Flow complet : enrollment (scan + World ID) et transaction (scan + Ledger + sign)

**Dépendances**

- *Reçoit* : API REST du Pi (Personne 1), endpoints backend (Personne 3), adresses smart contracts (Personne 4)
- *Fournit* : intégration UI pour World ID et Ledger, feedback sur les interfaces

### 5.3 Personne 3 — «Backend & Chainlink CRE»

**Rôle** : Responsable du serveur backend, de l'orchestration Chainlink CRE, et de la pipeline de vérification.

**Tâches détaillées**

- **T3.1 — Setup Backend Node.js (1h)** : Initialisation du projet Express + TypeScript. Configuration CORS, rate limiting, logging. Structure des routes : `/api/verify-worldid`, `/api/iris-match`, `/api/register-wallet`. Variables d'environnement (World App ID, Chainlink credentials).
- **T3.2 — Validation World ID Backend (3h)** : Endpoint `POST /api/verify-worldid` : reçoit la preuve ZKP de l'extension. Vérification via l'API World ID (`app_id`, `action`, `signal`, `proof`). Vérification du nullifier hash pour éviter les doubles inscriptions. Si valide, déclenche l'appel au smart contract pour enregistrer le binding. Gestion des erreurs : preuve invalide, nullifier déjà utilisé, timeout.
- **T3.3 — Stockage sécurisé des templates (2h)** : Service de stockage des templates iris chiffrés. Chaque template est stocké avec : le nullifier hash World ID comme clé, le template chiffré AES-256-GCM, le timestamp de création. Base de données : SQLite pour le hackathon (simple et portable). Le serveur ne peut jamais déchiffrer les templates (il ne possède pas la clé).
- **T3.4 — Chainlink CRE Workflow (6h)** : C'est le morceau le plus critique côté partenaire. Construction du workflow via CRE SDK TypeScript. Le workflow fait : (1) Reçoit le template iris chiffré via Confidential HTTP (trigger), (2) Récupère le template de référence via Confidential HTTP (les credentials API sont protégés), (3) Déchiffre et compare les templates dans l'environnement sécurisé (Hamming distance), (4) Retourne le résultat signé (match bool + confidence score). Simulation via CRE CLI. Tests avec les templates de test de la Personne 1.
- **T3.5 — Pipeline de vérification (2h)** : Orchestration du flow complet côté backend : (1) L'extension envoie le template chiffré + transaction à approuver, (2) Le backend déclenche le CRE workflow, (3) Le workflow retourne le résultat, (4) Si match, le backend soumet la preuve au smart contract, (5) Le smart contract autorise la transaction.
- **T3.6 — Monitoring & Logging (1h)** : Dashboard simple (terminal ou page web) montrant : les scans en cours, les résultats de matching, les transactions approuvées/rejetées. Utile pour la démo devant le jury.
- **T3.7 — Tests d'intégration (2h)** : Test end-to-end : scan Pi → template → CRE workflow → smart contract → transaction. Test de sécurité : envoi d'un mauvais template → rejet. Test de replay : même template envoyé deux fois → nonce check.

**Livrables**

- Backend déployé (localhost pour la démo, ou service cloud)
- CRE Workflow simulé avec succès via CRE CLI (minimum requis par Chainlink)
- Documentation de l'API backend (endpoints, payloads, erreurs)

**Dépendances**

- *Reçoit* : templates de test (Personne 1), contrats déployés + ABI (Personne 4)
- *Fournit* : endpoints API pour l'extension (Personne 2), résultats de vérification pour les contrats (Personne 4)

### 5.4 Personne 4 — «Smart Contracts & Blockchain»

**Rôle** : Responsable de tous les smart contracts, de leur déploiement sur World Chain, et de l'intégration on-chain.

**Tâches détaillées**

- **T4.1 — Setup Foundry/Hardhat (1h)** : Initialisation du projet Solidity avec Foundry (forge, cast, anvil). Configuration du réseau World Chain (testnet). Installation des dépendances : `@worldcoin/world-id-contracts`, `@chainlink/contracts`.
- **T4.2 — WorldIDVerifier.sol (3h)** : Contrat qui vérifie les preuves ZKP World ID 4.0. Hérite ou appelle le World ID Router contract déployé sur World Chain. Fonctions : `verifyAndRegister(address wallet, uint256 root, uint256 nullifierHash, uint256[8] proof)`. Stocke le mapping `nullifierHash => walletAddress`. Emits event `WalletRegistered(address wallet, uint256 nullifierHash)`.
- **T4.3 — IrisRegistry.sol (3h)** : Registre principal du binding iris-wallet. Mapping : `nullifierHash => WalletInfo (address, timestamp, active)`. Fonctions : `registerWallet()`, `getWallet()`, `isRegistered()`, `deactivateWallet()`. Modificateurs : `onlyVerified` (seul le WorldIDVerifier peut appeler), `uniqueNullifier` (un nullifier = un wallet). Events pour le tracking.
- **T4.4 — IrisVerifier.sol (4h)** : Contrat qui reçoit les résultats du CRE Workflow Chainlink. Implémente l'interface ChainlinkClient ou reçoit les callbacks du DON. Fonctions : `submitMatchResult(address wallet, bool matched, uint256 confidence, bytes signature)`, `isTransactionApproved(address wallet, bytes32 txHash)`. Logique anti-replay : chaque résultat de matching a un nonce unique. Timeout : un résultat de matching expire après N blocs.
- **T4.5 — Tests Solidity (3h)** : Tests unitaires pour chaque contrat via Foundry (`forge test`). Tests de sécurité : double registration, fausse preuve, overflow, reentrancy. Tests d'intégration : simulation du flow complet en local (anvil). Couverture de tests minimum 80%.
- **T4.6 — Déploiement World Chain (2h)** : Déploiement sur World Chain testnet via `forge script`. Vérification des contrats sur l'explorateur (Etherscan-like). Génération des ABI et adresses pour l'extension et le backend. Script de déploiement reproductible (`deploy.sh`).
- **T4.7 — Intégration Ledger Clear Signing (2h)** : Création des fichiers JSON Clear Signing pour chaque contrat. Description humainement lisible de chaque fonction (ex: 'Register your iris wallet', 'Approve transaction with iris scan'). Tests avec un device Ledger si disponible.
- **T4.8 — Documentation des contrats (1h)** : NatSpec comments dans chaque contrat. README avec les adresses déployées, les ABI, et les exemples d'appel. Diagramme de séquence des interactions inter-contrats.

**Livrables**

- 3 smart contracts déployés et vérifiés sur World Chain testnet
- ABI et adresses partagées avec l'équipe
- Suite de tests Foundry avec > 80% couverture
- Fichiers Clear Signing JSON pour Ledger

**Dépendances**

- *Reçoit* : format des résultats CRE (Personne 3), spécifications des appels depuis l'extension (Personne 2)
- *Fournit* : adresses et ABI des contrats (Personne 2 et 3), interface pour le CRE callback (Personne 3)

---

## 6. Planning Détaillé — 36 Heures de Hackathon

### Phase 1 — Foundation (Heures 0-8)

**Objectif** : chaque membre a son environnement prêt et les composants de base fonctionnent indépendamment.

| Heure | Personne 1 (Hardware) | Personne 2 (Extension) | Personne 3 (Backend/CRE) | Personne 4 (Contracts) |
|-------|----------------------|----------------------|--------------------------|----------------------|
| 0-2 | Setup Pi + caméra + LEDs | Scaffold extension Chrome | Setup Node.js + Express | Setup Foundry + World Chain |
| 2-4 | Capture vidéo + détection oeil | Provider injection (EIP-1193) | Routes API + World ID SDK | WorldIDVerifier.sol |
| 4-6 | Segmentation iris (Hough) | UI Enrollment (maquette) | Validation World ID | IrisRegistry.sol |
| 6-8 | Encodage IrisCode (Gabor) | Communication Pi HTTP | Stockage templates | IrisVerifier.sol (base) |

**Sync Point #1 (Heure 8)** : Chaque membre démontre son composant indépendamment. Le Pi peut scanner et générer un template. L'extension peut injecter un provider. Le backend peut valider une preuve World ID mock. Les contrats passent les tests unitaires.

### Phase 2 — Intégration (Heures 8-20)

**Objectif** : connecter les composants entre eux et faire fonctionner le flow de bout en bout.

| Heure | Personne 1 (Hardware) | Personne 2 (Extension) | Personne 3 (Backend/CRE) | Personne 4 (Contracts) |
|-------|----------------------|----------------------|--------------------------|----------------------|
| 8-10 | API REST Flask | Intégration World IDKit | CRE Workflow (trigger) | Déploiement World Chain |
| 10-12 | API REST tests | Intégration Ledger DMK | CRE Workflow (fetch + compute) | Tests intégration contrats |
| 12-14 | Anti-spoofing | UI Transaction popup | CRE Workflow (result) | Ledger Clear Signing JSON |
| 14-16 | Calibration seuil iris | Connect extension <-> Pi | CRE CLI simulation | Fix bugs + optimisation gas |
| 16-18 | Optimisation capture | Connect extension <-> backend | Pipeline vérification | Intégration CRE callback |
| 18-20 | Tests multi-utilisateurs | Flow enrollment complet | Tests end-to-end | Tests sécurité (fuzz) |

**Sync Point #2 (Heure 20)** : Le flow d'enrollment fonctionne de bout en bout : scan iris (Pi) → World ID (extension) → validation (backend) → registration (smart contract). Le CRE Workflow est simulé avec succès.

### Phase 3 — Polishing & Démo (Heures 20-36)

**Objectif** : flow de transaction complet, landing page, vidéo de démo, préparation du pitch.

| Heure | Personne 1 (Hardware) | Personne 2 (Extension) | Personne 3 (Backend/CRE) | Personne 4 (Contracts) |
|-------|----------------------|----------------------|--------------------------|----------------------|
| 20-24 | Démo physique (assemblage) | Flow transaction complet | Monitoring dashboard | Documentation NatSpec |
| 24-28 | Tests robustesse | Landing page (Next.js) | Déploiement backend | README + diagrammes |
| 28-32 | Backup hardware | Polish UI + animations | Tests de charge | Vérification contrats explorer |
| 32-34 | Répétition démo | Déploiement Vercel | Cleanup + logs | Préparation submission |
| 34-36 | **TOUS** : vidéo démo (3 min) + préparation pitch + soumission finale |

---

## 7. Risques et Stratégies de Mitigation

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| La caméra IR ne capture pas un iris de qualité suffisante | Élevée | Critique | Plan B : utiliser une webcam standard avec traitement logiciel. La qualité sera moindre mais le concept est démontrable. Avoir une image iris de test en fallback. |
| La segmentation iris échoue sur certains yeux | Moyenne | Élevé | Pré-calibrer avec les 4 yeux de l'équipe. Si un iris est difficile, utiliser les 3 autres pour la démo. Avoir un mode 'demo' avec template pré-enregistré. |
| World ID 4.0 SDK a des bugs ou changements récents | Faible | Élevé | Suivre exactement la doc officielle. Préparer un mock de World ID pour le développement local. Contacter l'équipe World présente au hackathon. |
| Le CRE Workflow ne compile pas ou la simulation échoue | Moyenne | Élevé | Commencer par les templates CRE officiels et modifier. Utiliser le bootcamp CRE comme guide pas-à-pas. Contacter l'équipe Chainlink sur place pour support. |
| Le Raspberry Pi n'est pas sur le même réseau que le laptop | Faible | Moyen | Prévoir un câble Ethernet USB direct Pi <-> laptop. Ou hotspot mobile dédié. |
| Pas assez de temps pour tout finir | Élevée | Élevé | Prioriser : (1) enrollment flow, (2) CRE simulation, (3) transaction flow. La landing page est bonus. Le minimum viable = scan + World ID + wallet créé. |
| L'intégration Ledger est plus complexe que prévu | Moyenne | Faible | Ledger est le partenaire le moins critique. Si trop complexe, le retirer et se concentrer sur World + Chainlink. Le track Ledger est un bonus. |

---

## 8. Critères de Jugement & Stratégie de Pitch

### 8.1 Ce que chaque partenaire veut voir

**World ($8,000)**

- World ID utilisé comme contrainte réelle, pas un gadget
- Validation de preuve dans un smart contract OU backend — les deux dans notre cas
- Use case innovant de proof of personhood

> **Notre angle** : *'World ID n'est pas un add-on, c'est le fondement. Sans World ID, IrisWallet n'existe pas. Chaque wallet est ancré dans une preuve d'unicité humaine.'*

**Ledger ($6,000)**

- Ledger comme trust layer (pas juste un hardware wallet)
- Human-in-the-loop pour les actions sensibles
- Clear Signing pour la transparence

> **Notre angle** : *'L'iris authentifie l'humain, Ledger authentifie la transaction. Double vérification : biométrique + hardware. C'est le standard de sécurité le plus élevé possible pour un wallet.'*

**Chainlink ($2,000)**

- CRE Workflow fonctionnel (simulé ou déployé)
- Utilisation de Confidential HTTP
- Privacy-preserving workflow

> **Notre angle** : *'Les données biométriques sont le type de données le plus sensible qui existe. Chainlink Confidential Compute garantit qu'elles ne sont jamais exposées. Le matching se fait dans un TEE, seul un booléen sort.'*

### 8.2 Structure du Pitch (3 minutes)

1. **0:00-0:30 — Le problème** : *'700 millions de dollars perdus en 2025 à cause de seed phrases volées ou perdues. Et si votre clé privée était quelque chose que vous ne pouvez ni perdre ni oublier ?'*
2. **0:30-1:00 — La solution** : *'IrisWallet : votre iris est votre wallet. Un scan, un wallet, une identité vérifiée.'* + démo live du scan
3. **1:00-2:00 — Démo live** : enrollment complet (scan → World ID → wallet créé) puis transaction (scan → match → Ledger sign → tx envoyée)
4. **2:00-2:30 — Architecture** : diagramme montrant les 3 partenaires et comment ils s'interconnectent
5. **2:30-3:00 — Vision** : *'Un monde où chaque être humain a un wallet qu'il ne peut pas perdre, lié à son identité biologique unique.'*

---

## 9. MVP — Ce qui DOIT marcher pour gagner

Si vous manquez de temps, voici la hiérarchie de priorité absolue :

**Tier 1 — Non-négociable** (sans ça, pas de prix)

1. Scan iris fonctionnel sur le Raspberry Pi qui génère un template
2. Vérification World ID 4.0 avec preuve validée on-chain ou backend
3. Création d'un wallet lié au nullifier World ID
4. CRE Workflow simulé avec succès (requis par Chainlink)

**Tier 2 — Fortement recommandé** (différenciateur)

5. Flow de transaction complet (re-scan → match → sign)
6. Extension Chrome fonctionnelle avec UI soignée
7. Intégration Ledger DMK
8. Smart contracts déployés et vérifiés sur World Chain

**Tier 3 — Bonus** (impressionne le jury)

9. Landing page déployée
10. Anti-spoofing fonctionnel
11. Dashboard de monitoring
12. Démo avec 4 utilisateurs différents

---

## 10. Structure des Repos & Soumission

### 10.1 Structure monorepo recommandée

Un seul repo GitHub avec la structure suivante :

```
iriswallet/
├── hardware/        — Code Raspberry Pi (Python)
├── extension/       — Extension Chrome (TypeScript/React)
├── backend/         — Serveur Node.js + CRE Workflow
├── contracts/       — Smart contracts Solidity (Foundry)
├── landing/         — Landing page (Next.js)
├── docs/            — Diagrammes, architecture, screenshots
└── README.md        — Description projet + setup instructions
```

### 10.2 Checklist de soumission

- **Nom du projet** : IrisWallet
- **Description courte** : Iris-authenticated blockchain wallet powered by World ID, Ledger, and Chainlink Confidential Compute
- **Repo GitHub** public avec README complet
- **Vidéo démo** (max 3 min) montrant le flow enrollment + transaction
- **Lien de démo live** (landing page Vercel + extension installée en local)
- **Adresses des smart contracts** déployés sur World Chain
- **Explication claire** de l'utilisation de chaque partenaire dans la description
