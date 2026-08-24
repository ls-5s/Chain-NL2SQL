import type { QueryResult } from "@/types/api";

export type ResultColumn = { label: string; prop: string; longText: boolean };

const longTextColumnPattern = /(?:content|description|summary|excerpt|detail|message|reason|text)/i;

export function resultCellText(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "string") return value;
  if (typeof value === "object") {
    try {
      return JSON.stringify(value, null, 2);
    } catch {
      return String(value);
    }
  }
  return String(value);
}

export function resultColumnIsLongText(result: QueryResult, label: string, columnIndex: number) {
  if (longTextColumnPattern.test(label)) return true;
  return result.rows.some((row) => {
    const value = row[columnIndex];
    return typeof value === "string" && value.length > 96;
  });
}

export function resultColumns(result: QueryResult): ResultColumn[] {
  return result.columns.map((label, columnIndex) => ({
    label,
    prop: label,
    longText: resultColumnIsLongText(result, label, columnIndex),
  }));
}
