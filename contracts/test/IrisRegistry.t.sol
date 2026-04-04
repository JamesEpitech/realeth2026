// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import {Test} from "forge-std/Test.sol";
import {IrisRegistry} from "../src/IrisRegistry.sol";

contract IrisRegistryTest is Test {
    IrisRegistry public registry;

    address public deployer = makeAddr("deployer");
    address public alice = makeAddr("alice");
    address public bob = makeAddr("bob");
    bytes32 public constant IRIS_1 = keccak256("iris_alice");
    bytes32 public constant IRIS_2 = keccak256("iris_bob");

    function setUp() public {
        vm.prank(deployer);
        registry = new IrisRegistry();
    }

    function test_registerWallet() public {
        registry.registerWallet(alice, IRIS_1);

        IrisRegistry.WalletInfo memory info = registry.getWallet(IRIS_1);
        assertEq(info.wallet, alice);
        assertTrue(info.active);
        assertGt(info.registeredAt, 0);
        assertTrue(registry.isRegistered(IRIS_1));
        assertTrue(registry.isActive(IRIS_1));
        assertEq(registry.totalRegistered(), 1);
        assertEq(registry.walletToIrisHash(alice), IRIS_1);
    }

    function test_registerWallet_emitsEvent() public {
        vm.expectEmit(true, true, false, false);
        emit IrisRegistry.WalletRegistered(IRIS_1, alice);
        registry.registerWallet(alice, IRIS_1);
    }

    function test_revert_doubleRegistration() public {
        registry.registerWallet(alice, IRIS_1);

        vm.expectRevert(abi.encodeWithSelector(IrisRegistry.AlreadyRegistered.selector, IRIS_1));
        registry.registerWallet(bob, IRIS_1);
    }

    function test_revert_walletAlreadyBound() public {
        registry.registerWallet(alice, IRIS_1);

        vm.expectRevert(abi.encodeWithSelector(IrisRegistry.WalletAlreadyBound.selector, alice));
        registry.registerWallet(alice, IRIS_2);
    }

    function test_deactivateWallet() public {
        registry.registerWallet(alice, IRIS_1);

        vm.prank(alice);
        registry.deactivateWallet(IRIS_1);

        assertFalse(registry.isActive(IRIS_1));
        assertTrue(registry.isRegistered(IRIS_1));
    }

    function test_deactivateWallet_byOwner() public {
        registry.registerWallet(alice, IRIS_1);

        vm.prank(deployer);
        registry.deactivateWallet(IRIS_1);

        assertFalse(registry.isActive(IRIS_1));
    }

    function test_revert_deactivate_notOwnerOrWallet() public {
        registry.registerWallet(alice, IRIS_1);

        vm.prank(bob);
        vm.expectRevert(IrisRegistry.OnlyOwnerOrWallet.selector);
        registry.deactivateWallet(IRIS_1);
    }

    function test_revert_deactivate_alreadyDeactivated() public {
        registry.registerWallet(alice, IRIS_1);

        vm.prank(alice);
        registry.deactivateWallet(IRIS_1);

        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(IrisRegistry.AlreadyDeactivated.selector, IRIS_1));
        registry.deactivateWallet(IRIS_1);
    }

    function test_reactivateWallet() public {
        registry.registerWallet(alice, IRIS_1);

        vm.prank(alice);
        registry.deactivateWallet(IRIS_1);
        assertFalse(registry.isActive(IRIS_1));

        vm.prank(alice);
        registry.reactivateWallet(IRIS_1);
        assertTrue(registry.isActive(IRIS_1));
    }

    function test_revert_reactivate_alreadyActive() public {
        registry.registerWallet(alice, IRIS_1);

        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(IrisRegistry.AlreadyActive.selector, IRIS_1));
        registry.reactivateWallet(IRIS_1);
    }

    function test_revert_deactivate_notRegistered() public {
        vm.prank(deployer);
        vm.expectRevert(abi.encodeWithSelector(IrisRegistry.NotRegistered.selector, IRIS_1));
        registry.deactivateWallet(IRIS_1);
    }

    function test_isRegistered_falseByDefault() public view {
        assertFalse(registry.isRegistered(IRIS_1));
    }

    function test_multipleRegistrations() public {
        registry.registerWallet(alice, IRIS_1);
        registry.registerWallet(bob, IRIS_2);

        assertEq(registry.totalRegistered(), 2);
        assertTrue(registry.isRegistered(IRIS_1));
        assertTrue(registry.isRegistered(IRIS_2));
    }
}
