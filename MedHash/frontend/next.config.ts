
const nextConfig = {
  // Remove output: 'standalone' or 'export' - let Amplify handle it
  images: {
    unoptimized: true,
  },
  trailingSlash: true,
};

module.exports = nextConfig;