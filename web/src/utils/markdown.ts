const HTML_ESCAPE_RE = /[&<>"']/g;
const HTML_ESCAPE_MAP: Record<string, string> = {
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#39;",
};

function escapeHtml(value: string): string {
  return value.replace(HTML_ESCAPE_RE, (character) => HTML_ESCAPE_MAP[character]);
}

function safeHref(value: string): string | null {
  const href = value.trim();
  return /^(?:https?:\/\/|mailto:|#|\/)/i.test(href) ? href : null;
}

function renderInlineMarkdown(value: string): string {
  const codeTokens: string[] = [];
  const tokenized = value
    .replace(/```(?:([\w+-]+)[ \t]+)?([\s\S]*?)```/g, (_match, language: string | undefined, code: string) => {
      const token = `\u0000code-${codeTokens.length}\u0000`;
      const languageClass = language ? ` class="language-${escapeHtml(language)}"` : "";
      codeTokens.push(`<code${languageClass}>${escapeHtml(code)}</code>`);
      return token;
    })
    .replace(/`([^`\n]+)`/g, (_match, code: string) => {
    const token = `\u0000code-${codeTokens.length}\u0000`;
    codeTokens.push(`<code>${escapeHtml(code)}</code>`);
    return token;
    });

  let html = escapeHtml(tokenized);
  html = html.replace(/!\[([^\]]*)\]\(([^)\s]+)(?:\s+"([^"]*)")?\)/g, (_match, alt: string, source: string, title?: string) => {
    const href = safeHref(source);
    if (!href) return escapeHtml(alt);
    const titleAttribute = title ? ` title="${escapeHtml(title)}"` : "";
    return `<img src="${escapeHtml(href)}" alt="${escapeHtml(alt)}"${titleAttribute} loading="lazy">`;
  });
  html = html.replace(/\[([^\]]+)\]\(([^)\s]+)(?:\s+"([^"]*)")?\)/g, (_match, label: string, target: string, title?: string) => {
    const href = safeHref(target);
    if (!href) return label;
    const titleAttribute = title ? ` title="${escapeHtml(title)}"` : "";
    return `<a href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer"${titleAttribute}>${label}</a>`;
  });
  html = html
    .replace(/\*\*([^*\n]+)\*\*|__([^_\n]+)__/g, (_match, strongA?: string, strongB?: string) => `<strong>${strongA ?? strongB ?? ""}</strong>`)
    .replace(/~~([^~\n]+)~~/g, "<del>$1</del>")
    .replace(/(?<!\*)\*([^*\n]+)\*(?!\*)|(?<!\w)_([^_\n]+)_(?!\w)/g, (_match, italicA?: string, italicB?: string) => `<em>${italicA ?? italicB ?? ""}</em>`);

  return html.replace(/\u0000code-(\d+)\u0000/g, (_match, index: string) => codeTokens[Number(index)] ?? "");
}

function renderParagraph(lines: string[]): string {
  return `<p>${renderInlineMarkdown(lines.join("\n")).replace(/\n/g, "<br>")}</p>`;
}

export function renderMarkdown(markdown: string): string {
  const lines = markdown.replace(/\r\n?/g, "\n").split("\n");
  const blocks: string[] = [];
  let paragraph: string[] = [];
  let listType: "ul" | "ol" | null = null;
  let listItems: string[] = [];
  let quoteLines: string[] = [];
  let codeLanguage = "";
  let codeLines: string[] = [];
  let inCode = false;

  const flushParagraph = () => {
    if (paragraph.length) blocks.push(renderParagraph(paragraph));
    paragraph = [];
  };
  const flushList = () => {
    if (listType && listItems.length) blocks.push(`<${listType}>${listItems.map((item) => `<li>${renderInlineMarkdown(item)}</li>`).join("")}</${listType}>`);
    listType = null;
    listItems = [];
  };
  const flushQuote = () => {
    if (quoteLines.length) blocks.push(`<blockquote>${renderParagraph(quoteLines)}</blockquote>`);
    quoteLines = [];
  };

  for (const line of lines) {
    const fence = line.match(/^\s*```\s*([\w+-]*)\s*$/);
    if (fence) {
      if (inCode) {
        blocks.push(`<pre><code${codeLanguage ? ` class="language-${escapeHtml(codeLanguage)}"` : ""}>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
        codeLanguage = "";
        codeLines = [];
        inCode = false;
      } else {
        flushParagraph();
        flushList();
        flushQuote();
        codeLanguage = fence[1] ?? "";
        inCode = true;
      }
      continue;
    }
    if (inCode) {
      codeLines.push(line);
      continue;
    }

    const heading = line.match(/^\s*(#{1,6})\s+(.+?)\s*#*\s*$/);
    if (heading) {
      flushParagraph();
      flushList();
      flushQuote();
      const level = heading[1].length;
      blocks.push(`<h${level}>${renderInlineMarkdown(heading[2])}</h${level}>`);
      continue;
    }
    const quote = line.match(/^\s*>\s?(.*)$/);
    if (quote) {
      flushParagraph();
      flushList();
      quoteLines.push(quote[1]);
      continue;
    }
    const unordered = line.match(/^\s*[-*+]\s+(.+)$/);
    const ordered = line.match(/^\s*\d+[.)]\s+(.+)$/);
    if (unordered || ordered) {
      flushParagraph();
      flushQuote();
      const nextType = unordered ? "ul" : "ol";
      if (listType && listType !== nextType) flushList();
      listType = nextType;
      listItems.push((unordered ?? ordered)?.[1] ?? "");
      continue;
    }
    if (!line.trim()) {
      flushParagraph();
      flushList();
      flushQuote();
      continue;
    }
    flushList();
    flushQuote();
    paragraph.push(line);
  }

  if (inCode) blocks.push(`<pre><code${codeLanguage ? ` class="language-${escapeHtml(codeLanguage)}"` : ""}>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
  flushParagraph();
  flushList();
  flushQuote();
  return blocks.join("");
}
