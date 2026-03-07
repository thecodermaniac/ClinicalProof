const hre = require("hardhat");

async function main() {
  const MedHash = await hre.ethers.getContractFactory("MedHash");
  const medHash = await MedHash.deploy();
  
  await medHash.waitForDeployment();
  
  const address = await medHash.getAddress();
  console.log("MedHash deployed to:", address);
  
  // Save this address for your frontend
  console.log("\n✅ Add this to your frontend .env.local:");
  console.log(`NEXT_PUBLIC_CONTRACT_ADDRESS=${address}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});