/** @type {import('next').NextConfig} */
const nextConfig = {
  // Disable image optimization to reduce memory
  images: {
    unoptimized: true
  },
  
  // Experimental features
  experimental: {
    // Reduce memory usage during build
    webpackMemoryOptimizations: true,
  },
  
  // Optimize build performance
  webpack: (config, { dev, isServer }) => {
    if (!dev && !isServer) {
      // Optimize for production builds
      config.optimization = {
        ...config.optimization,
        splitChunks: {
          chunks: 'all',
          cacheGroups: {
            vendor: {
              test: /[\\/]node_modules[\\/]/,
              name: 'vendors',
              chunks: 'all',
            },
          },
        },
      };
    }
    return config;
  },
};

module.exports = nextConfig;