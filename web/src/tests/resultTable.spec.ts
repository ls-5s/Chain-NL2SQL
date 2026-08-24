import { describe, expect, it } from "vitest";

import { renderMarkdown } from "@/utils/markdown";
import { resultCellText, resultColumns } from "@/utils/resultTable";

describe("query result table formatting", () => {
  it("normalizes empty and structured cell values", () => {
    expect(resultCellText(null)).toBe("—");
    expect(resultCellText("")).toBe("—");
    expect(resultCellText({ id: 1, active: true })).toBe('{\n  "id": 1,\n  "active": true\n}');
    expect(resultCellText(12)).toBe("12");
  });

  it("identifies long text columns by name or content length", () => {
    const columns = resultColumns({
      columns: ["id", "title", "content", "notes"],
      rows: [[1, "Order", "**Markdown** body", "x".repeat(97)]],
      row_count: 1,
      truncated: false,
    });

    expect(columns.map((column) => column.longText)).toEqual([false, false, true, true]);
  });

  it("renders Markdown while escaping raw HTML", () => {
    const html = renderMarkdown("## Title\n\n**bold** and <script>alert(1)</script>");

    expect(html).toContain("<h2>Title</h2>");
    expect(html).toContain("<strong>bold</strong>");
    expect(html).toContain("&lt;script&gt;alert(1)&lt;/script&gt;");
    expect(html).not.toContain("<script>");
  });
});
