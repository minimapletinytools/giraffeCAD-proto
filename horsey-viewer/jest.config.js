module.exports = {
  testEnvironment: 'node',
  testMatch: ['**/__tests__/**/*.js', '**/?(*.)+(spec|test).js'],
  collectCoverageFrom: [
    'file-watcher.js',
    'runner-session.js',
    'viewer.js',
    '!node_modules/**',
  ],
};
