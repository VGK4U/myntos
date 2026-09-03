/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: 'http://127.0.0.1:8000/api/v1/:path*',
      },
      {
        source: '/app',
        destination: '/app.html',
      },
      {
        source: '/download-app',
        destination: '/app.html',
      },
      {
        source: '/download/mobile.apk',
        destination: '/MyntReal.apk',
      },
      {
        source: '/download/apk',
        destination: '/MyntReal.apk',
      },
      {
        source: '/mobile.apk',
        destination: '/MyntReal.apk',
      },
    ];
  },
};

module.exports = nextConfig;