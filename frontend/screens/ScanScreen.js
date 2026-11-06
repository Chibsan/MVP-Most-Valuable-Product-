import React, { useState, useEffect, useRef } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  ActivityIndicator,
  ScrollView,
  Platform,
} from "react-native";
import { CameraView, Camera } from "expo-camera";
import { Picker } from "@react-native-picker/picker";

import { API_URL } from "../config";

const CATEGORIES = [
  { label: "✨ Auto-detect Category", value: "auto" },
  { label: "Meat & Poultry", value: "meat" },
  { label: "Cheese", value: "cheese" },
  { label: "Dairy & Milk", value: "dairy" },
  { label: "Bakery & Bread", value: "bakery" },
  { label: "Snacks & Treats", value: "snacks" },
  { label: "Drinks & Beverages", value: "drinks" },
  { label: "General Grocery", value: "general" },
];

export default function ScanScreen({ navigation }) {
  const [hasPermission, setHasPermission] = useState(null);
  const [scanned, setScanned] = useState(false);
  const [loading, setLoading] = useState(false);
  const [category, setCategory] = useState("auto");
  const [scannedBarcode, setScannedBarcode] = useState(null);
  const [scannedProduct, setScannedProduct] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);
  const [manualBarcode, setManualBarcode] = useState("");
  const [showManualInput, setShowManualInput] = useState(Platform.OS === "web");

  const isScanningRef = useRef(false);

  useEffect(() => {
    const getCameraPermissions = async () => {
      const { status } = await Camera.requestCameraPermissionsAsync();
      setHasPermission(status === "granted");
    };
    getCameraPermissions();
  }, []);

  const processBarcode = async (barcodeToFetch) => {
    const cleanBarcode = barcodeToFetch.trim();
    if (!cleanBarcode) return;

    isScanningRef.current = true;
    setScanned(true);
    setScannedBarcode(cleanBarcode);
    setLoading(true);
    setErrorMsg(null);
    setScannedProduct(null);

    console.log(`[ScanScreen] Contacting backend at ${API_URL}/products for barcode: ${cleanBarcode}`);

    try {
      const response = await fetch(`${API_URL}/products`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          barcode: cleanBarcode,
          category: category,
        }),
      });

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }

      const product = await response.json();
      console.log("[ScanScreen] Successfully saved and received product:", product);
      setScannedProduct(product);
    } catch (error) {
      console.error("[ScanScreen] Error saving product:", error);
      setErrorMsg(
        `Failed to reach backend at ${API_URL}. Check if your backend container is running and on the same network.`
      );
    } finally {
      setLoading(false);
    }
  };

  const handleBarCodeScanned = ({ data, type }) => {
    if (isScanningRef.current || scanned || !data) return;
    isScanningRef.current = true;
    console.log(`[ScanScreen] Barcode detected by camera: ${data} (format: ${type})`);
    processBarcode(data);
  };

  const handleRescan = () => {
    isScanningRef.current = false;
    setScanned(false);
    setScannedBarcode(null);
    setScannedProduct(null);
    setErrorMsg(null);
  };

  const handleManualSubmit = () => {
    if (manualBarcode.trim()) {
      processBarcode(manualBarcode);
      setManualBarcode("");
    }
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
        <Text style={styles.errorText}>Camera permission was denied.</Text>
        <Text style={styles.subtitle}>You can still enter barcodes manually below:</Text>
        <TextInput
          style={styles.manualInput}
          placeholder="e.g. 7340191149779"
          value={manualBarcode}
          onChangeText={setManualBarcode}
          keyboardType="numeric"
        />
        <TouchableOpacity style={styles.manualSubmitBtn} onPress={handleManualSubmit}>
          <Text style={styles.buttonText}>Submit Barcode</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Camera Viewport with sibling overlay */}
      <View style={styles.cameraWrapper}>
        <CameraView
          style={styles.camera}
          facing="back"
          barcodeScannerSettings={{
            barcodeTypes: ["qr", "ean13", "ean8", "upc_a", "upc_e", "code128", "code39"],
          }}
          onBarcodeScanned={scanned ? undefined : handleBarCodeScanned}
        />

        {!scanned && (
          <View style={styles.overlay} pointerEvents="none">
            <View style={styles.scanTarget} />
            <Text style={styles.hintText}>
              {Platform.OS === "web"
                ? "Desktop webcam active • Enter barcode below"
                : "Center barcode inside frame"}
            </Text>
          </View>
        )}
      </View>

      {/* Control Panel below the camera */}
      <ScrollView
        style={styles.controls}
        contentContainerStyle={styles.controlsContent}
        keyboardShouldPersistTaps="handled"
      >
        {loading && (
          <View style={styles.statusBox}>
            <ActivityIndicator size="small" color="#4A90E2" />
            <Text style={styles.statusText}>
              Scanned: {scannedBarcode} — Looking up on Open Food Facts...
            </Text>
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
              Category: {scannedProduct.category.toUpperCase()} {category === "auto" ? "✨ (auto-detected)" : ""}
            </Text>

            {scannedProduct.nutrition_facts && scannedProduct.nutrition_facts.length > 0 ? (
              <View style={styles.nutrientRow}>
                {scannedProduct.nutrition_facts.slice(0, 4).map((f) => (
                  <View key={f.metric} style={styles.nutrientPill}>
                    <Text style={styles.pillLabel}>{f.metric}</Text>
                    <Text style={styles.pillValue}>
                      {f.value !== null ? `${f.value} ${f.unit}` : "-"}
                    </Text>
                  </View>
                ))}
              </View>
            ) : (
              <Text style={styles.noFactsText}>No nutrition facts recorded yet</Text>
            )}
          </View>
        )}

        {!scanned && (
          <>
            <Text style={styles.label}>Category to assign:</Text>
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

        {scanned ? (
          <TouchableOpacity style={styles.rescanButton} onPress={handleRescan}>
            <Text style={styles.buttonText}>Scan Another Barcode</Text>
          </TouchableOpacity>
        ) : (
          <TouchableOpacity
            style={styles.toggleManualBtn}
            onPress={() => setShowManualInput(!showManualInput)}
          >
            <Text style={styles.toggleManualText}>
              {showManualInput ? "Hide Manual Input" : "Or Enter Barcode Manually"}
            </Text>
          </TouchableOpacity>
        )}

        {showManualInput && !scanned && (
          <View style={styles.manualBox}>
            <TextInput
              style={styles.manualInput}
              placeholder="e.g. 6414891801020"
              value={manualBarcode}
              onChangeText={setManualBarcode}
              onSubmitEditing={handleManualSubmit}
              returnKeyType="search"
              keyboardType="numeric"
            />
            <TouchableOpacity style={styles.manualSubmitBtn} onPress={handleManualSubmit}>
              <Text style={styles.buttonText}>Look Up</Text>
            </TouchableOpacity>
          </View>
        )}

        <TouchableOpacity
          style={styles.rankingButton}
          onPress={() => navigation.navigate("Ranking")}
        >
          <Text style={styles.buttonText}>View Category Rankings</Text>
        </TouchableOpacity>
      </ScrollView>
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
  cameraWrapper: {
    flex: 1,
    position: "relative",
    backgroundColor: "#000",
  },
  camera: {
    flex: 1,
    width: "100%",
  },
  overlay: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: "center",
    alignItems: "center",
  },
  scanTarget: {
    width: 260,
    height: 140,
    borderWidth: 2,
    borderColor: "#4A90E2",
    borderRadius: 12,
    backgroundColor: "rgba(255,255,255,0.08)",
  },
  hintText: {
    color: "#fff",
    marginTop: 12,
    fontSize: 14,
    backgroundColor: "rgba(0,0,0,0.6)",
    paddingHorizontal: 12,
    paddingVertical: 5,
    borderRadius: 8,
  },
  controls: {
    maxHeight: 330,
    backgroundColor: "#ffffff",
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
  },
  controlsContent: {
    padding: 16,
  },
  label: { fontSize: 13, fontWeight: "600", color: "#444", marginBottom: 4 },
  pickerContainer: {
    borderWidth: 1,
    borderColor: "#ddd",
    borderRadius: 8,
    marginBottom: 10,
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
  statusText: { marginLeft: 8, color: "#4A90E2", fontWeight: "600", fontSize: 13 },
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
  noFactsText: { fontSize: 12, color: "#999", marginTop: 6, fontStyle: "italic" },
  rescanButton: {
    backgroundColor: "#FF9500",
    padding: 14,
    borderRadius: 8,
    alignItems: "center",
    marginBottom: 8,
  },
  toggleManualBtn: {
    alignItems: "center",
    paddingVertical: 6,
    marginBottom: 8,
  },
  toggleManualText: {
    color: "#4A90E2",
    fontSize: 14,
    fontWeight: "600",
  },
  manualBox: {
    flexDirection: "row",
    gap: 8,
    marginBottom: 10,
  },
  manualInput: {
    flex: 1,
    borderWidth: 1,
    borderColor: "#ccc",
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    fontSize: 14,
    backgroundColor: "#fafafa",
  },
  manualSubmitBtn: {
    backgroundColor: "#34A853",
    paddingHorizontal: 16,
    justifyContent: "center",
    borderRadius: 8,
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
  subtitle: { fontSize: 14, color: "#666", marginTop: 6, textAlign: "center", marginBottom: 12 },
});
