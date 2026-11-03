export type Metric =
  | "calories"
  | "carbohydrates"
  | "protein"
  | "fat"
  | "fibre"
  | "price";
export type Direction = "most" | "least";
export type PreferenceMode = "default" | "custom";
export type QualityStatus =
  | "reliable"
  | "unreliable"
  | "unverified"
  | "missing"
  | "invalid";

export interface Category {
  slug: string;
  name: string;
  product_count: number;
  is_active: boolean;
  source_url: string | null;
}

export interface Criterion {
  metric: Metric;
  direction: Direction;
  unit: string;
}

export interface Preference {
  category: string | null;
  preference_mode: PreferenceMode;
  primary_metric: Metric;
  primary_direction: Direction;
  criteria: Criterion[];
}

export interface MetricResult {
  value: number | null;
  unit: string;
  direction: Direction;
  rank: number | null;
  quality_status: QualityStatus;
  reason: string | null;
  source_url: string | null;
  observed_at: string | null;
}

export interface ComparedProduct {
  id: string;
  name: string;
  category: string;
  brand: string | null;
  barcode: string | null;
  display_position: number;
  package_size_g: number | null;
  package_size_label: string | null;
  package_price: number | null;
  currency: "EUR" | null;
  price_per_100g: number | null;
  price_source: string | null;
  price_observed_at: string | null;
  source_url: string | null;
  metrics: Record<Metric, MetricResult>;
}

export interface Comparison {
  category: string;
  preference_mode: PreferenceMode;
  primary_metric: Metric;
  primary_direction: Direction;
  criteria: Criterion[];
  items: ComparedProduct[];
  unranked_count: number;
}

export interface PreferenceUpdate {
  category: string;
  preference_mode: PreferenceMode;
  primary_metric?: Metric;
  primary_direction?: Direction;
}

export interface ApiErrorBody {
  code: string;
  message: string;
}
