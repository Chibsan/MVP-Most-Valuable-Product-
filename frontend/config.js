import Constants from 'expo-constants';

// Automatically resolve the backend URL to the host machine running Expo
const hostUri =
  Constants.expoConfig?.hostUri ||
  Constants.manifest2?.extra?.expoClient?.hostUri ||
  '';

const hostIp = hostUri ? hostUri.split(':')[0] : 'localhost';

export const API_URL = `http://${hostIp}:8000`;
