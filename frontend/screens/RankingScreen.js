import React, { useState, useEffect } from "react";
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
} from "react-native";
import { useIsFocused } from "@react-navigation/native";

import { API_URL } from "../config";

export default function RankingScreen({ navigation }) {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const isFocused = useIsFocused();

  useEffect(() => {
    if (isFocused) {
      fetchRanking();
    }
  }, [isFocused]);

  const fetchRanking = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/products/ranking`);
      const data = await response.json();
      setProducts(data);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const renderItem = ({ item, index }) => (
    <View style={styles.item}>
      <Text style={styles.rank}>#{index + 1}</Text>
      <View style={styles.info}>
        <Text style={styles.barcode}>Barcode: {item.barcode}</Text>
        <Text style={styles.category}>Category: {item.category}</Text>
      </View>
      <Text style={styles.score}>{item.score.toFixed(1)} pts</Text>
    </View>
  );

  return (
    <View style={styles.container}>
      {loading ? (
        <ActivityIndicator size="large" color="#4A90E2" style={{ flex: 1 }} />
      ) : (
        <FlatList
          data={products}
          keyExtractor={(item) => item.id.toString()}
          renderItem={renderItem}
          ListEmptyComponent={
            <Text style={styles.empty}>No products scanned yet.</Text>
          }
        />
      )}

      <TouchableOpacity
        style={styles.button}
        onPress={() => navigation.navigate("Scan")}
      >
        <Text style={styles.buttonText}>Add Products</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f5f5f5" },
  item: {
    flexDirection: "row",
    backgroundColor: "white",
    padding: 15,
    marginVertical: 8,
    marginHorizontal: 16,
    borderRadius: 8,
    alignItems: "center",
  },
  rank: { fontSize: 20, fontWeight: "bold", color: "#4A90E2", width: 40 },
  info: { flex: 1, marginLeft: 10 },
  barcode: { fontSize: 16, fontWeight: "bold" },
  category: { fontSize: 14, color: "#666", textTransform: "capitalize" },
  score: { fontSize: 18, fontWeight: "bold", color: "#333" },
  empty: { textAlign: "center", marginTop: 50, fontSize: 16, color: "#999" },
  button: {
    backgroundColor: "#4A90E2",
    padding: 15,
    margin: 20,
    borderRadius: 8,
    alignItems: "center",
  },
  buttonText: { color: "white", fontSize: 18, fontWeight: "bold" },
});
