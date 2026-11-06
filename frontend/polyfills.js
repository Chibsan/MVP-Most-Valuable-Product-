import { Platform } from 'react-native';

// Ensure Expo global JSI bridge objects are present before module imports on mobile
if (Platform.OS !== 'web') {
  try {
    const { installExpoGlobalPolyfill } = require('expo-modules-core/src/polyfill/dangerous-internal');
    if (!globalThis.expo?.EventEmitter) {
      installExpoGlobalPolyfill();
    }
  } catch (e) {
    // Polyfill safely bypassed if unnecessary
  }
}

