import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';

export default function HomeScreen({ navigation }) {
  return (
    <View style={styles.container}>
      <Text style={styles.logo}>MVP4U</Text>
      <Text style={styles.subtitle}>Your Ultimate Product Scanner</Text>
      
      <TouchableOpacity 
        style={styles.button}
        onPress={() => navigation.navigate('Scan')}
      >
        <Text style={styles.buttonText}>Scan Products</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#f5f5f5' },
  logo: { fontSize: 48, fontWeight: 'bold', color: '#4A90E2', marginBottom: 10 },
  subtitle: { fontSize: 16, color: '#666', marginBottom: 40 },
  button: { backgroundColor: '#4A90E2', padding: 15, borderRadius: 8, width: '80%', alignItems: 'center' },
  buttonText: { color: 'white', fontSize: 18, fontWeight: '600' }
});
