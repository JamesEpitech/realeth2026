// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

/// @title IrisRegistry
/// @author IrisWallet Team — ETHGlobal Cannes 2026
/// @notice Registry that binds iris-authenticated wallets to unique iris hashes.
/// @dev Each iris hash can only have one wallet. Wallets can be deactivated and reactivated.
contract IrisRegistry {
    /// @notice Information about a registered wallet.
    /// @param wallet The wallet address.
    /// @param registeredAt Timestamp of registration.
    /// @param active Whether the wallet is currently active.
    struct WalletInfo {
        address wallet;
        uint256 registeredAt;
        bool active;
    }

    /// @notice The contract owner (deployer).
    address public owner;

    /// @notice Maps iris hashes to their wallet info.
    mapping(bytes32 => WalletInfo) public wallets;

    /// @notice Maps wallet addresses to their iris hash.
    mapping(address => bytes32) public walletToIrisHash;

    /// @notice Total number of registered wallets.
    uint256 public totalRegistered;

    /// @notice Emitted when a new wallet is registered.
    event WalletRegistered(bytes32 indexed irisHash, address indexed wallet);

    /// @notice Emitted when a wallet is deactivated.
    event WalletDeactivated(bytes32 indexed irisHash, address indexed wallet);

    /// @notice Emitted when a wallet is reactivated.
    event WalletReactivated(bytes32 indexed irisHash, address indexed wallet);

    error NotRegistered(bytes32 irisHash);
    error AlreadyRegistered(bytes32 irisHash);
    error WalletAlreadyBound(address wallet);
    error AlreadyActive(bytes32 irisHash);
    error AlreadyDeactivated(bytes32 irisHash);
    error OnlyOwnerOrWallet();

    /// @notice Restricts access to the contract owner or the wallet itself.
    modifier onlyOwnerOrWallet(bytes32 irisHash) {
        if (msg.sender != owner && msg.sender != wallets[irisHash].wallet) {
            revert OnlyOwnerOrWallet();
        }
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    /// @notice Registers a new wallet bound to an iris hash.
    /// @dev Reverts if the iris hash or wallet is already registered.
    /// @param wallet The wallet address to register.
    /// @param irisHash The unique iris biometric hash (SHA-256 of IrisCode).
    function registerWallet(address wallet, bytes32 irisHash) external {
        if (wallets[irisHash].wallet != address(0)) {
            revert AlreadyRegistered(irisHash);
        }
        if (walletToIrisHash[wallet] != bytes32(0)) {
            revert WalletAlreadyBound(wallet);
        }

        wallets[irisHash] = WalletInfo({
            wallet: wallet,
            registeredAt: block.timestamp,
            active: true
        });
        walletToIrisHash[wallet] = irisHash;
        totalRegistered++;

        emit WalletRegistered(irisHash, wallet);
    }

    /// @notice Deactivates a registered wallet. Only callable by the owner or the wallet itself.
    /// @param irisHash The iris hash of the wallet to deactivate.
    function deactivateWallet(bytes32 irisHash) external onlyOwnerOrWallet(irisHash) {
        WalletInfo storage info = wallets[irisHash];
        if (info.wallet == address(0)) revert NotRegistered(irisHash);
        if (!info.active) revert AlreadyDeactivated(irisHash);

        info.active = false;
        emit WalletDeactivated(irisHash, info.wallet);
    }

    /// @notice Reactivates a previously deactivated wallet. Only callable by the owner or the wallet itself.
    /// @param irisHash The iris hash of the wallet to reactivate.
    function reactivateWallet(bytes32 irisHash) external onlyOwnerOrWallet(irisHash) {
        WalletInfo storage info = wallets[irisHash];
        if (info.wallet == address(0)) revert NotRegistered(irisHash);
        if (info.active) revert AlreadyActive(irisHash);

        info.active = true;
        emit WalletReactivated(irisHash, info.wallet);
    }

    /// @notice Returns the full wallet info for a given iris hash.
    /// @param irisHash The iris hash to look up.
    /// @return The WalletInfo struct.
    function getWallet(bytes32 irisHash) external view returns (WalletInfo memory) {
        return wallets[irisHash];
    }

    /// @notice Checks whether an iris hash has a registered wallet.
    /// @param irisHash The iris hash to check.
    /// @return True if registered.
    function isRegistered(bytes32 irisHash) external view returns (bool) {
        return wallets[irisHash].wallet != address(0);
    }

    /// @notice Checks whether a registered wallet is currently active.
    /// @param irisHash The iris hash to check.
    /// @return True if active.
    function isActive(bytes32 irisHash) external view returns (bool) {
        return wallets[irisHash].active;
    }
}
