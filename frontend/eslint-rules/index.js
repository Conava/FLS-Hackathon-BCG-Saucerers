"use strict";

/**
 * eslint-plugin-wellness
 *
 * Custom ESLint plugin that enforces wellness-framing compliance across
 * TypeScript and TSX source files.
 *
 * Rules:
 *   wellness/no-diagnostic-verbs — flags string literals and JSX text nodes
 *   that contain banned medical/diagnostic verbs.
 *
 * See CLAUDE.md key invariants for rationale (MDR Class IIa avoidance).
 */

/**
 * Banned terms and their word-boundary regex patterns.
 * Multi-word phrases ("prevent disease") use a space-literal match.
 * Single words use \b word boundaries so that identifiers like
 * `treatmentPlanId` are NOT flagged — only string content is checked.
 */
const BANNED_TERMS = [
  "diagnose",
  "diagnosis",
  "treat",
  "treatment",
  "cure",
  "cures",
  "heal",
  "heals",
  "prevent disease",
];

function buildPattern(term) {
  if (term.includes(" ")) {
    return new RegExp(term, "i");
  }
  return new RegExp(`\\b${term}\\b`, "i");
}

const BANNED_PATTERNS = BANNED_TERMS.map((term) => ({
  term,
  pattern: buildPattern(term),
}));

/**
 * Check a string value and report if any banned term is found.
 *
 * @param {import("eslint").Rule.RuleContext} context
 * @param {import("eslint").AST.Node} node
 * @param {string} text
 */
function checkText(context, node, text) {
  for (const { term, pattern } of BANNED_PATTERNS) {
    if (pattern.test(text)) {
      context.report({
        node,
        message:
          `Banned diagnostic verb "${term}" found in string literal. ` +
          "Use wellness framing instead (support/manage/track/optimize). " +
          "See CLAUDE.md key invariants.",
      });
      // Report once per node even if multiple terms match
      return;
    }
  }
}

/** @type {import("eslint").Rule.RuleModule} */
const noDiagnosticVerbsRule = {
  meta: {
    type: "problem",
    docs: {
      description:
        "Disallow diagnostic/medical verbs in string literals to maintain wellness framing",
      recommended: true,
      url: "https://github.com/FLS-Hackathon-BCG-Saucerers/CLAUDE.md",
    },
    schema: [],
    messages: {
      bannedVerb:
        'Banned diagnostic verb "{{term}}" found. Use wellness framing (support/manage/track). See CLAUDE.md.',
    },
  },

  create(context) {
    return {
      // String literals: "diagnose this"
      Literal(node) {
        if (typeof node.value === "string") {
          checkText(context, node, node.value);
        }
      },

      // Template literal quasis: `diagnose ${x}`
      TemplateElement(node) {
        const raw = node.value && node.value.raw;
        if (typeof raw === "string") {
          checkText(context, node, raw);
        }
      },

      // JSX text nodes: <p>diagnose you</p>
      JSXText(node) {
        if (typeof node.value === "string") {
          checkText(context, node, node.value);
        }
      },
    };
  },
};

module.exports = {
  rules: {
    "no-diagnostic-verbs": noDiagnosticVerbsRule,
  },
  configs: {
    recommended: {
      plugins: ["wellness"],
      rules: {
        "wellness/no-diagnostic-verbs": "error",
      },
    },
  },
};
