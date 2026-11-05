import React, { useState, useEffect } from "react";
import { View, Text, StyleSheet, TouchableOpacity } from "react-native";
import { CameraView, Camera } from "expo-camera";
import { Picker } from "@react-native-picker/picker";

import { API_URL } from "../config";

export default function ScanScreen({ navigation }) {
  const [hasPermission, setHasPermission] = useState(null);
  const [scanned, setScanned] = useState(false);
  const [category, setCategory] = useState("protein");

  useEffect(() => {
    const getCameraPermissions = async () => {
      const { status } = await Camera.requestCameraPermissionsAsync();
      setHasPermission(status === "granted");
    };
    getCameraPermissions();
  }, []);

  const handleBarCodeScanned = async ({ type, data }) => {
    setScanned(true);
    alert(`Barcode ${data} scanned! Adding to database...`);

    try {
      const response = await fetch(`${API_URL}/products`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          barcode: data,
          category: category,
          score: Math.random() * 100,
        }),
      });
      const result = await response.json();
      console.log("Saved product:", result);
    } catch (error) {
      console.error("Error saving product:", error);
      alert("Error saving product. Check backend connection.");
    }
  };

  if (hasPermission === null)
    return <Text>Requesting for camera permission...</Text>;
  if (hasPermission === false) return <Text>No access to camera</Text>;

  return (
    <View style={styles.container}>
      <CameraView
        style={styles.camera}
        onBarcodeScanned={scanned ? undefined : handleBarCodeScanned}
        barcodeScannerSettings={{
          barcodeTypes: ["qr", "ean13", "ean8", "upc_a", "upc_e"],
        }}
      />
      <View style={styles.controls}>
        <Text style={styles.label}>Select Category:</Text>
        <View style={styles.pickerContainer}>
          <Picker
            selectedValue={category}
            onValueChange={(itemValue) => setCategory(itemValue)}
          >
            <Picker.Item label="Protein" value="protein" />
            <Picker.Item label="Fiber" value="fiber" />
            <Picker.Item label="Price" value="price" />
          </Picker>
        </View>

        {scanned && (
          <TouchableOpacity
            style={styles.rescanButton}
            onPress={() => setScanned(false)}
          >
            <Text style={styles.buttonText}>Tap to Scan Again</Text>
          </TouchableOpacity>
        )}

        <TouchableOpacity
          style={styles.rankingButton}
          onPress={() => navigation.navigate("Ranking")}
        >
          <Text style={styles.buttonText}>See Ranking</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fff" },
  camera: { flex: 1 },
  controls: {
    padding: 20,
    backgroundColor: "#f9f9f9",
    borderTopWidth: 1,
    borderColor: "#ddd",
  },
  label: { fontSize: 16, marginBottom: 10, fontWeight: "bold" },
  pickerContainer: {
    borderWidth: 1,
    borderColor: "#ccc",
    borderRadius: 8,
    marginBottom: 20,
  },
  rescanButton: {
    backgroundColor: "#FF9500",
    padding: 15,
    borderRadius: 8,
    alignItems: "center",
    marginBottom: 10,
  },
  rankingButton: {
    backgroundColor: "#4A90E2",
    padding: 15,
    borderRadius: 8,
    alignItems: "center",
  },
  buttonText: { color: "white", fontSize: 16, fontWeight: "bold" },
});
