/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',  // Add this for static export
  images: {
    unoptimized: true, // Required for static export
  },
  trailingSlash: true,
};

module.exports = nextConfig;