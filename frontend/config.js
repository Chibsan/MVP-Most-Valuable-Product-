import { Platform } from 'react-native';
import Constants from 'expo-constants';

// Automatically resolve the backend URL for web, local network, or remote host
let hostIp = 'localhost';

if (Platform.OS === 'web' && typeof window !== 'undefined' && window.location?.hostname) {
  hostIp = window.location.hostname;
} else {
  const hostUri =
    Constants.expoConfig?.hostUri ||
    Constants.manifest2?.extra?.expoClient?.hostUri ||
    '';
  hostIp = hostUri ? hostUri.split(':')[0] : 'localhost';
}

export const API_URL = `http://${hostIp}:8000`;

