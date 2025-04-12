module.exports = {
  transpileDependencies: ['/@yabby-business/'],
  devServer: {
    // host: 'localhost',
    port: 8080,
    proxy: {
      '/api' : {
        target: 'http://localhost:5000',
        ws: true,
        changeOrigin: true,
        pathRewrite: {
          '^/api': ''
        }
      }
    },
    // disableHostCheck: true,
  }
}
