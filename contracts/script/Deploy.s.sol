// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import {Script, console} from "forge-std/Script.sol";
import {IrisRegistry} from "../src/IrisRegistry.sol";
import {IrisVerifier} from "../src/IrisVerifier.sol";

contract Deploy is Script {
    uint256 constant EXPIRATION_BLOCKS = 50;

    function run() external {
        address oracle = vm.envAddress("ORACLE_ADDRESS");
        uint256 deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");

        vm.startBroadcast(deployerPrivateKey);

        // 1. Deploy IrisRegistry
        IrisRegistry irisRegistry = new IrisRegistry();
        console.log("IrisRegistry deployed at:", address(irisRegistry));

        // 2. Deploy IrisVerifier
        IrisVerifier irisVerifier = new IrisVerifier(irisRegistry, oracle, EXPIRATION_BLOCKS);
        console.log("IrisVerifier deployed at:", address(irisVerifier));

        vm.stopBroadcast();

        // Summary
        console.log("\n=== DEPLOYMENT SUMMARY ===");
        console.log("Chain:", block.chainid);
        console.log("IrisRegistry:", address(irisRegistry));
        console.log("IrisVerifier:", address(irisVerifier));
        console.log("Oracle:      ", oracle);
        console.log("Expiration:  ", EXPIRATION_BLOCKS, "blocks");
    }
}
