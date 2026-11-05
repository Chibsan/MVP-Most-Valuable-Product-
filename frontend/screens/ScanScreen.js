import React, { useState, useEffect } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
} from "react-native";
import { CameraView, Camera } from "expo-camera";
import { Picker } from "@react-native-picker/picker";

import { API_URL } from "../config";

const CATEGORIES = [
  { label: "Cheese", value: "cheese" },
  { label: "Dairy & Milk", value: "dairy" },
  { label: "Meat & Plant-based", value: "meat" },
  { label: "Snacks & Treats", value: "snacks" },
  { label: "General Grocery", value: "general" },
];

export default function ScanScreen({ navigation }) {
  const [hasPermission, setHasPermission] = useState(null);
  const [scanned, setScanned] = useState(false);
  const [loading, setLoading] = useState(false);
  const [category, setCategory] = useState("cheese");
  const [scannedProduct, setScannedProduct] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  useEffect(() => {
    const getCameraPermissions = async () => {
      const { status } = await Camera.requestCameraPermissionsAsync();
      setHasPermission(status === "granted");
    };
    getCameraPermissions();
  }, []);

  const handleBarCodeScanned = async ({ data }) => {
    setScanned(true);
    setLoading(true);
    setErrorMsg(null);
    setScannedProduct(null);

    try {
      const response = await fetch(`${API_URL}/products`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          barcode: data,
          category: category,
        }),
      });

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }

      const product = await response.json();
      setScannedProduct(product);
    } catch (error) {
      console.error("Error saving product:", error);
      setErrorMsg("Failed to save product. Ensure backend is running and reachable.");
    } finally {
      setLoading(false);
    }
  };

  const handleRescan = () => {
    setScanned(false);
    setScannedProduct(null);
    setErrorMsg(null);
  };

  if (hasPermission === null) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#4A90E2" />
        <Text style={styles.loadingText}>Requesting camera permission...</Text>
      </View>
    );
  }

  if (hasPermission === false) {
    return (
      <View style={styles.centerContainer}>
        <Text style={styles.errorText}>Camera access denied.</Text>
        <Text style={styles.subtitle}>Please enable camera permissions in app settings.</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <CameraView
        style={styles.camera}
        onBarcodeScanned={scanned ? undefined : handleBarCodeScanned}
        barcodeScannerSettings={{
          barcodeTypes: ["qr", "ean13", "ean8", "upc_a", "upc_e"],
        }}
      >
        <View style={styles.overlay}>
          <View style={styles.scanTarget} />
          <Text style={styles.hintText}>Point camera at barcode</Text>
        </View>
      </CameraView>

      <View style={styles.controls}>
        {loading && (
          <View style={styles.statusBox}>
            <ActivityIndicator size="small" color="#4A90E2" />
            <Text style={styles.statusText}>Looking up product on Open Food Facts...</Text>
          </View>
        )}

        {errorMsg && (
          <View style={styles.errorBox}>
            <Text style={styles.errorBoxText}>{errorMsg}</Text>
          </View>
        )}

        {scannedProduct && (
          <View style={styles.productCard}>
            <Text style={styles.productTitle}>
              {scannedProduct.name || `Barcode ${scannedProduct.barcode}`}
            </Text>
            {scannedProduct.brand && (
              <Text style={styles.productBrand}>Brand: {scannedProduct.brand}</Text>
            )}
            <Text style={styles.productCategory}>
              Category: {scannedProduct.category.toUpperCase()}
            </Text>

            {scannedProduct.nutrition_facts && scannedProduct.nutrition_facts.length > 0 && (
              <View style={styles.nutrientRow}>
                {scannedProduct.nutrition_facts.slice(0, 3).map((f) => (
                  <View key={f.metric} style={styles.nutrientPill}>
                    <Text style={styles.pillLabel}>{f.metric}</Text>
                    <Text style={styles.pillValue}>
                      {f.value !== null ? `${f.value} ${f.unit}` : "-"}
                    </Text>
                  </View>
                ))}
              </View>
            )}
          </View>
        )}

        {!scanned && (
          <>
            <Text style={styles.label}>Select Category to Assign:</Text>
            <View style={styles.pickerContainer}>
              <Picker
                selectedValue={category}
                onValueChange={(val) => setCategory(val)}
              >
                {CATEGORIES.map((c) => (
                  <Picker.Item key={c.value} label={c.label} value={c.value} />
                ))}
              </Picker>
            </View>
          </>
        )}

        {scanned && (
          <TouchableOpacity style={styles.rescanButton} onPress={handleRescan}>
            <Text style={styles.buttonText}>Scan Another Barcode</Text>
          </TouchableOpacity>
        )}

        <TouchableOpacity
          style={styles.rankingButton}
          onPress={() => navigation.navigate("Ranking")}
        >
          <Text style={styles.buttonText}>View Category Rankings</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#000" },
  centerContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 20,
    backgroundColor: "#f5f5f5",
  },
  camera: { flex: 1 },
  overlay: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },
  scanTarget: {
    width: 250,
    height: 150,
    borderWidth: 2,
    borderColor: "#4A90E2",
    borderRadius: 12,
    backgroundColor: "rgba(255,255,255,0.05)",
  },
  hintText: {
    color: "#fff",
    marginTop: 12,
    fontSize: 14,
    backgroundColor: "rgba(0,0,0,0.6)",
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 8,
  },
  controls: {
    padding: 16,
    backgroundColor: "#ffffff",
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
  },
  label: { fontSize: 14, fontWeight: "600", color: "#333", marginBottom: 6 },
  pickerContainer: {
    borderWidth: 1,
    borderColor: "#ddd",
    borderRadius: 8,
    marginBottom: 12,
    backgroundColor: "#fafafa",
  },
  statusBox: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    padding: 10,
    backgroundColor: "#eef6ff",
    borderRadius: 8,
    marginBottom: 10,
  },
  statusText: { marginLeft: 8, color: "#4A90E2", fontWeight: "600" },
  errorBox: {
    padding: 10,
    backgroundColor: "#ffebee",
    borderRadius: 8,
    marginBottom: 10,
  },
  errorBoxText: { color: "#d32f2f", fontSize: 13, textAlign: "center" },
  productCard: {
    padding: 12,
    backgroundColor: "#f0f7ff",
    borderRadius: 8,
    borderLeftWidth: 4,
    borderLeftColor: "#4A90E2",
    marginBottom: 12,
  },
  productTitle: { fontSize: 16, fontWeight: "bold", color: "#1a1a1a" },
  productBrand: { fontSize: 13, color: "#555", marginTop: 2 },
  productCategory: { fontSize: 12, color: "#888", marginTop: 2, fontWeight: "500" },
  nutrientRow: { flexDirection: "row", marginTop: 8, gap: 6 },
  nutrientPill: {
    backgroundColor: "#fff",
    paddingVertical: 4,
    paddingHorizontal: 8,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: "#d0e3ff",
  },
  pillLabel: { fontSize: 10, color: "#666", textTransform: "capitalize" },
  pillValue: { fontSize: 12, fontWeight: "bold", color: "#4A90E2" },
  rescanButton: {
    backgroundColor: "#FF9500",
    padding: 14,
    borderRadius: 8,
    alignItems: "center",
    marginBottom: 8,
  },
  rankingButton: {
    backgroundColor: "#4A90E2",
    padding: 14,
    borderRadius: 8,
    alignItems: "center",
  },
  buttonText: { color: "#fff", fontSize: 15, fontWeight: "bold" },
  loadingText: { marginTop: 10, color: "#666" },
  errorText: { fontSize: 18, fontWeight: "bold", color: "#d32f2f" },
  subtitle: { fontSize: 14, color: "#666", marginTop: 6, textAlign: "center" },
});
