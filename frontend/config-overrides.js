const { override, addWebpackResolve } = require('customize-cra');
const path = require('path');

module.exports = override(
  addWebpackResolve({
    fullySpecified: false,
    extensions: ['.ts', '.tsx', '.js', '.jsx'],
    fallback: {
      "buffer": path.resolve(__dirname, 'node_modules/buffer/index.js'),
      "crypto": path.resolve(__dirname, 'node_modules/crypto-browserify/index.js'),
      "stream": path.resolve(__dirname, 'node_modules/stream-browserify/index.js'),
      "assert": path.resolve(__dirname, 'node_modules/assert/index.js'),
      "http": path.resolve(__dirname, 'node_modules/stream-http/index.js'),
      "https": path.resolve(__dirname, 'node_modules/https-browserify/index.js'),
      "os": path.resolve(__dirname, 'node_modules/os-browserify/browser.js'),
      "url": path.resolve(__dirname, 'node_modules/url/url.js'),
      "util": path.resolve(__dirname, 'node_modules/util/util.js'),
      "zlib": path.resolve(__dirname, 'node_modules/browserify-zlib/src/index.js'),
      "path": path.resolve(__dirname, 'node_modules/path-browserify/index.js'),
      "fs": false,
      "net": false,
      "tls": false
    }
  })
);