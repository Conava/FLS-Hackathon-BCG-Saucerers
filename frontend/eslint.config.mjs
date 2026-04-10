import { dirname, resolve } from "path";
import { fileURLToPath } from "url";
import { createRequire } from "module";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Load the CJS wellness plugin via createRequire so it works in an ESM config
const require = createRequire(import.meta.url);
const wellnessPlugin = require(resolve(__dirname, "eslint-rules/index.js"));

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

const eslintConfig = [
  // Existing Next.js rules (unchanged)
  ...compat.extends("next/core-web-vitals", "next/typescript"),

  // Wellness framing lint — applies to src/**/*.{ts,tsx} but NOT test files
  // (test files legitimately reference banned terms as test data)
  {
    files: ["src/**/*.ts", "src/**/*.tsx"],
    ignores: ["src/**/__tests__/**", "src/**/*.test.ts", "src/**/*.test.tsx"],
    plugins: {
      wellness: wellnessPlugin,
    },
    rules: {
      "wellness/no-diagnostic-verbs": "error",
    },
  },
];

export default eslintConfig;
