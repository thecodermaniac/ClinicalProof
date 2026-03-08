const hre = require("hardhat");

async function main() {
  console.log("🚀 Deploying MedHash contract to Sepolia...");
  
  const MedHash = await hre.ethers.getContractFactory("MedHash");
  const medHash = await MedHash.deploy();
  
  await medHash.waitForDeployment();
  
  const address = await medHash.getAddress();
  console.log("✅ MedHash deployed to:", address);
  
  // Wait for a few confirmations
  console.log("⏳ Waiting for confirmations...");
  await medHash.deploymentTransaction().wait(5);
  
  // Verify on Etherscan
  console.log("🔍 Verifying contract on Etherscan...");
  try {
    await hre.run("verify:verify", {
      address: address,
      constructorArguments: [],
    });
    console.log("✅ Contract verified on Etherscan");
  } catch (error) {
    console.log("⚠️ Verification failed:", error.message);
  }
  
  // Save address to file
  const fs = require('fs');
  fs.writeFileSync('contract-address.txt', address);
  
  console.log("\n📝 IMPORTANT: Add this to your frontend .env file:");
  console.log(`NEXT_PUBLIC_CONTRACT_ADDRESS=${address}`);
  console.log("NEXT_PUBLIC_NETWORK_ID=11155111"); // Sepolia chain ID
  
  return address;
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });