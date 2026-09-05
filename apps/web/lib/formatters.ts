/**
 * Pure presentation-layer formatters for realistic synthetic customer names
 * and compact order/payment display identifiers.
 *
 * NOTE: These formatters transform ONLY UI presentation strings and NEVER mutate
 * underlying database IDs, API contracts, or backend parameters.
 */

const SYNTHETIC_MERCHANTS = [
  "Northstar Foods",
  "Orbit Retail",
  "Meridian Labs",
  "Acme Health",
  "Kora Systems",
  "Vertex Commerce",
  "Aura Logistics",
  "Pinnacle Brands",
  "Cascade Digital",
  "Solstice Media",
];

export function formatSyntheticCustomerName(rawName: string | null | undefined, caseOrCustomerId: number | string): string {
  if (rawName && !rawName.includes("Demo Customer") && !rawName.includes("No Action Customer")) {
    return rawName;
  }
  const idNum = typeof caseOrCustomerId === "number" ? caseOrCustomerId : parseInt(String(caseOrCustomerId).replace(/\D/g, "") || "0", 10);
  const index = Math.abs(idNum) % SYNTHETIC_MERCHANTS.length;
  return SYNTHETIC_MERCHANTS[index];
}

export function formatCompactId(rawId: string | null | undefined, prefix: "ORD" | "PAY" | "CASE"): string {
  if (!rawId) return `${prefix}-001`;

  // If already clean compact format like ORD-194D744, return as is
  if (rawId.startsWith(`${prefix}-`)) return rawId;

  // Extract trailing hex/num hash if present
  const cleanHash = rawId.replace(/^(ord_demo_|pay_demo_|cust_demo_|ord_|pay_)/, "").toUpperCase();

  if (cleanHash.length > 7) {
    return `${prefix}-${cleanHash.slice(-7)}`;
  }
  return `${prefix}-${cleanHash}`;
}
