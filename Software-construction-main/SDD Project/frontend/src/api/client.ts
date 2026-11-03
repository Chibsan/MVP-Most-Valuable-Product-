import type {
  ApiErrorBody,
  Category,
  Comparison,
  Metric,
  Preference,
  PreferenceUpdate,
} from "../types/api";

const apiBase = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!response.ok) {
    let message = `Request failed (${response.status}).`;
    try {
      const body = (await response.json()) as ApiErrorBody;
      if (body.message) message = body.message;
    } catch (error) {
      if (!(error instanceof SyntaxError)) throw error;
    }
    throw new ApiError(message, response.status);
  }
  return (await response.json()) as T;
}

export function getCategories(): Promise<{ items: Category[] }> {
  return request("/categories");
}

export function getPreference(): Promise<Preference> {
  return request("/preferences");
}

export function savePreference(update: PreferenceUpdate): Promise<Preference> {
  return request("/preferences", {
    method: "PUT",
    body: JSON.stringify(update),
  });
}

export function compare(
  update: PreferenceUpdate,
): Promise<Comparison> {
  return request("/comparisons", {
    method: "POST",
    body: JSON.stringify(update),
  });
}

export const metricLabels: Record<Metric, string> = {
  calories: "Calories",
  carbohydrates: "Carbohydrates",
  protein: "Protein",
  fat: "Fat",
  fibre: "Fibre",
  price: "Price per 100 g",
};
