/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: 'http://localhost:8000/api/v1/:path*',
      },
    ]
  },

  // 优化开发时的热重载
  webpack: (config, { dev, isServer }) => {
    // 开发环境下优化文件监听
    if (dev && !isServer) {
      config.watchOptions = {
        poll: 1000, // 每秒检查一次文件变化
        aggregateTimeout: 300, // 延迟300ms后重新构建
        ignored: /node_modules/,
      }
    }
    return config
  },

  // 禁用开发时的X-Powered-By头
  poweredByHeader: false,

  // 优化图片加载
  images: {
    remotePatterns: [],
  },

  // 开发环境下的优化
  experimental: {
    // 确保CSS更改能立即反映
    optimizeCss: false,
  },
}

module.exports = nextConfig
