// Ensure Expo global JSI bridge objects are present before module imports
import { installExpoGlobalPolyfill } from 'expo-modules-core/src/polyfill/dangerous-internal';

if (!globalThis.expo?.EventEmitter) {
  installExpoGlobalPolyfill();
}

