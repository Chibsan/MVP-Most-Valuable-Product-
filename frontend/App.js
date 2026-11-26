import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import HomeScreen from './screens/HomeScreen';
import ScanScreen from './screens/ScanScreen';
import RankingScreen from './screens/RankingScreen';

const Stack = createNativeStackNavigator();

export default function App() {
  return (
    <NavigationContainer>
      <Stack.Navigator initialRouteName="Home">
        <Stack.Screen name="Home" component={HomeScreen} options={{ title: 'MVP4U' }} />
        <Stack.Screen name="Scan" component={ScanScreen} options={{ title: 'Scan Product' }} />
        <Stack.Screen name="Ranking" component={RankingScreen} options={{ title: 'Product Ranking' }} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
