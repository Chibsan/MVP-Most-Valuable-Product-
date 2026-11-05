import React, { useState, useEffect } from "react";
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  ScrollView,
} from "react-native";
import { useIsFocused } from "@react-navigation/native";

import { API_URL } from "../config";

const METRIC_OPTIONS = [
  { label: "Most Protein", metric: "protein", direction: "most" },
  { label: "Least Calories", metric: "calories", direction: "least" },
  { label: "Least Fat", metric: "fat", direction: "least" },
  { label: "Most Fibre", metric: "fibre", direction: "most" },
  { label: "Least Carbs", metric: "carbohydrates", direction: "least" },
];

export default function RankingScreen({ navigation }) {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeMetric, setActiveMetric] = useState(METRIC_OPTIONS[0]);
  const isFocused = useIsFocused();

  useEffect(() => {
    if (isFocused) {
      fetchRanking(activeMetric);
    }
  }, [isFocused, activeMetric]);

  const fetchRanking = async (metricOption = activeMetric) => {
    setLoading(true);
    try {
      const url = `${API_URL}/products/ranking?metric=${metricOption.metric}&direction=${metricOption.direction}`;
      const response = await fetch(url);
      if (response.ok) {
        const data = await response.json();
        setProducts(data);
      } else {
        console.error("Failed to fetch rankings, status:", response.status);
      }
    } catch (error) {
      console.error("Error fetching rankings:", error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleMetricSelect = (opt) => {
    setActiveMetric(opt);
  };

  const renderItem = ({ item }) => {
    const isRanked = item.rank !== null && item.rank !== undefined;
    const primaryVal = item.primary_value;
    const primaryUnit = item.metrics?.[item.primary_metric]?.unit || "";

    return (
      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <View style={[styles.rankBadge, !isRanked && styles.unrankedBadge]}>
            <Text style={styles.rankText}>
              {isRanked ? `#${item.rank}` : "N/R"}
            </Text>
          </View>

          <View style={styles.headerInfo}>
            <Text style={styles.productName} numberOfLines={2}>
              {item.name || `Product ${item.barcode}`}
            </Text>
            {item.brand && <Text style={styles.productBrand}>{item.brand}</Text>}
          </View>

          <View style={styles.primaryValueContainer}>
            <Text style={styles.primaryValue}>
              {primaryVal !== null ? `${primaryVal}` : "N/A"}
            </Text>
            <Text style={styles.primaryUnit}>{primaryUnit}</Text>
          </View>
        </View>

        {item.metrics && (
          <View style={styles.metricsRow}>
            {Object.entries(item.metrics).map(([mKey, mData]) => {
              if (mKey === item.primary_metric) return null;
              return (
                <View key={mKey} style={styles.miniMetric}>
                  <Text style={styles.miniLabel}>{mKey.slice(0, 4)}</Text>
                  <Text style={styles.miniVal}>
                    {mData.value !== null ? `${mData.value}` : "-"}
                  </Text>
                </View>
              );
            })}
          </View>
        )}

        <View style={styles.footerRow}>
          <Text style={styles.barcodeText}>Barcode: {item.barcode}</Text>
          <Text style={styles.categoryBadge}>{item.category.toUpperCase()}</Text>
        </View>
      </View>
    );
  };

  return (
    <View style={styles.container}>
      {/* Metric Selector Tabs */}
      <View style={styles.metricBar}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false}>
          {METRIC_OPTIONS.map((opt) => {
            const isActive =
              opt.metric === activeMetric.metric && opt.direction === activeMetric.direction;
            return (
              <TouchableOpacity
                key={`${opt.metric}-${opt.direction}`}
                style={[styles.chip, isActive && styles.activeChip]}
                onPress={() => handleMetricSelect(opt)}
              >
                <Text style={[styles.chipText, isActive && styles.activeChipText]}>
                  {opt.label}
                </Text>
              </TouchableOpacity>
            );
          })}
        </ScrollView>
      </View>

      {/* Main List */}
      {loading && !refreshing ? (
        <ActivityIndicator size="large" color="#4A90E2" style={styles.loader} />
      ) : (
        <FlatList
          data={products}
          keyExtractor={(item) => item.id.toString()}
          renderItem={renderItem}
          refreshing={refreshing}
          onRefresh={() => {
            setRefreshing(true);
            fetchRanking();
          }}
          contentContainerStyle={styles.listContent}
          ListEmptyComponent={
            <View style={styles.emptyContainer}>
              <Text style={styles.emptyTitle}>No products scanned yet</Text>
              <Text style={styles.emptySubtitle}>
                Scan your first grocery barcode to see its nutritional ranking!
              </Text>
            </View>
          }
        />
      )}

      {/* Bottom CTA Button */}
      <TouchableOpacity
        style={styles.scanButton}
        onPress={() => navigation.navigate("Scan")}
      >
        <Text style={styles.scanButtonText}>Scan Another Product</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f5f6f8" },
  metricBar: {
    backgroundColor: "#ffffff",
    paddingVertical: 10,
    paddingHorizontal: 8,
    borderBottomWidth: 1,
    borderColor: "#e4e6eb",
  },
  chip: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: "#f0f2f5",
    marginHorizontal: 4,
  },
  activeChip: {
    backgroundColor: "#4A90E2",
  },
  chipText: {
    fontSize: 13,
    fontWeight: "600",
    color: "#4b4f56",
  },
  activeChipText: {
    color: "#ffffff",
  },
  loader: { flex: 1, justifyContent: "center", alignItems: "center" },
  listContent: { padding: 12, paddingBottom: 80 },
  card: {
    backgroundColor: "#ffffff",
    borderRadius: 10,
    padding: 14,
    marginBottom: 10,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 3,
    elevation: 2,
  },
  cardHeader: {
    flexDirection: "row",
    alignItems: "center",
  },
  rankBadge: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: "#e8f2ff",
    justifyContent: "center",
    alignItems: "center",
    marginRight: 10,
  },
  unrankedBadge: {
    backgroundColor: "#f0f0f0",
  },
  rankText: {
    fontSize: 15,
    fontWeight: "bold",
    color: "#4A90E2",
  },
  headerInfo: { flex: 1 },
  productName: {
    fontSize: 15,
    fontWeight: "700",
    color: "#1c1e21",
  },
  productBrand: {
    fontSize: 12,
    color: "#606770",
    marginTop: 2,
  },
  primaryValueContainer: {
    alignItems: "flex-end",
    marginLeft: 8,
  },
  primaryValue: {
    fontSize: 18,
    fontWeight: "bold",
    color: "#1c1e21",
  },
  primaryUnit: {
    fontSize: 11,
    color: "#8a8d91",
  },
  metricsRow: {
    flexDirection: "row",
    marginTop: 10,
    paddingTop: 10,
    borderTopWidth: 1,
    borderColor: "#f0f2f5",
    gap: 8,
  },
  miniMetric: {
    flex: 1,
    backgroundColor: "#f8f9fa",
    paddingVertical: 4,
    borderRadius: 6,
    alignItems: "center",
  },
  miniLabel: {
    fontSize: 10,
    color: "#8a8d91",
    textTransform: "uppercase",
  },
  miniVal: {
    fontSize: 12,
    fontWeight: "600",
    color: "#333",
  },
  footerRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: 8,
  },
  barcodeText: {
    fontSize: 11,
    color: "#999",
  },
  categoryBadge: {
    fontSize: 10,
    fontWeight: "bold",
    color: "#4A90E2",
    backgroundColor: "#eef6ff",
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  emptyContainer: {
    alignItems: "center",
    justifyContent: "center",
    marginTop: 60,
    paddingHorizontal: 20,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: "bold",
    color: "#333",
  },
  emptySubtitle: {
    fontSize: 14,
    color: "#888",
    textAlign: "center",
    marginTop: 6,
  },
  scanButton: {
    position: "absolute",
    bottom: 16,
    left: 16,
    right: 16,
    backgroundColor: "#4A90E2",
    paddingVertical: 14,
    borderRadius: 10,
    alignItems: "center",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 4,
    elevation: 4,
  },
  scanButtonText: {
    color: "#ffffff",
    fontSize: 16,
    fontWeight: "bold",
  },
});
