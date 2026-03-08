const nextConfig = {
  output: 'standalone',  // Change from 'export' to 'standalone'
  images: {
    unoptimized: true,
  },
  trailingSlash: true,
};

module.exports = nextConfig;