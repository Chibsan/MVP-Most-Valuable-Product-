import { Platform } from 'react-native';
import Constants from 'expo-constants';

export function resolveApiUrl() {
  let hostname = 'localhost';
  let isHttps = false;

  if (Platform.OS === 'web' && typeof window !== 'undefined' && window.location) {
    hostname = window.location.hostname || 'localhost';
    isHttps = window.location.protocol === 'https:';
  } else {
    const hostUri =
      Constants.expoConfig?.hostUri ||
      Constants.manifest2?.extra?.expoClient?.hostUri ||
      '';
    hostname = hostUri ? hostUri.split(':')[0] : 'localhost';
  }

  // GitHub Codespaces: port 8081 subdomain -> port 8000 subdomain over HTTPS
  if (hostname.endsWith('.app.github.dev')) {
    const backendHost = hostname.replace(/-8081(?=\.app\.github\.dev$)/, '-8000');
    return `https://${backendHost}`;
  }

  // Gitpod: port 8081 prefix -> port 8000 prefix over HTTPS
  if (hostname.includes('.gitpod.io')) {
    const backendHost = hostname.replace(/^8081-/, '8000-');
    return `https://${backendHost}`;
  }

  // Standard Local / LAN development
  const protocol = isHttps ? 'https:' : 'http:';
  return `${protocol}//${hostname}:8000`;
}

export const API_URL = resolveApiUrl();

