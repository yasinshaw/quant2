module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'jsdom',
  transform: {
    '^.+\\.(ts|tsx)$': ['ts-jest', {
      tsconfig: {
        jsx: 'react',
        esModuleInterop: true,
        allowSyntheticDefaultImports: true,
      },
    }],
  },
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
    '^.+\\.(css|less|scss|sass)$': 'identity-obj-proxy',
  },
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  testMatch: ['**/__tests__/**/*.test.tsx'],
  transformIgnorePatterns: [
    'node_modules/(?!(react-day-picker)/)',
  ],
  collectCoverageFrom: [
    'components/**/*.{ts,tsx}',
    '!components/**/*.d.ts',
    '!components/**/*.stories.tsx',
  ],
};
