// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract MedHash {
    struct Proof {
        bytes32 hash;
        uint256 timestamp;
        string pmid;
        string summaryType;
    }
    
    mapping(bytes32 => Proof) public proofs;
    mapping(string => bytes32[]) public paperProofs;
    
    event ProofStored(bytes32 indexed hash, string pmid, string summaryType, uint256 timestamp);
    
    function storeProof(
        string memory _pmid,
        string memory _summaryType,
        string memory _summaryHash
    ) public returns (bytes32) {
        bytes32 key = keccak256(abi.encodePacked(_pmid, _summaryType, _summaryHash));
        require(proofs[key].timestamp == 0, "Proof already exists");
        
        proofs[key] = Proof(key, block.timestamp, _pmid, _summaryType);
        paperProofs[_pmid].push(key);
        
        emit ProofStored(key, _pmid, _summaryType, block.timestamp);
        return key;
    }
    
    function verifyProof(
        string memory _pmid,
        string memory _summaryType,
        string memory _summaryHash
    ) public view returns (bool exists, uint256 timestamp) {
        bytes32 key = keccak256(abi.encodePacked(_pmid, _summaryType, _summaryHash));
        Proof memory proof = proofs[key];
        return (proof.timestamp > 0, proof.timestamp);
    }
    
    function getPaperProofs(string memory _pmid) public view returns (bytes32[] memory) {
        return paperProofs[_pmid];
    }
}