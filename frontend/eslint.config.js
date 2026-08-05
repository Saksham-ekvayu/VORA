import js from "@eslint/js";
import globals from "globals";
import react from "eslint-plugin-react";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";

export default [
  { ignores: ["dist", "node_modules", "eslint.config.js"] },
  {
    files: ["**/*.{js,jsx}"],
    linterOptions: {
      reportUnusedDisableDirectives: "off",
    },
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
      parserOptions: {
        ecmaVersion: "latest",
        ecmaFeatures: { jsx: true },
        sourceType: "module",
      },
    },
    plugins: {
      react,
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      // ESLint recommended rules
      ...js.configs.recommended.rules,
      // React Hooks rules (strict)
      ...reactHooks.configs.recommended.rules,
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "error",
      // Disable rules that cause runtime issues with the plugin + ESLint versions
      "react/display-name": "off",
      // Disable overly strict rules from newer react-hooks plugin versions
      "react-hooks/set-state-in-effect": "off",
      "react-hooks/purity": "off",
      "react-hooks/refs": "off",
      "react-hooks/use-memo": "off",
      "react-hooks/preserve-manual-memoization": "off",
      "react-hooks/static-components": "off",
      "react/prop-types": "off", // we use TypeScript for type checking

      // React Refresh rules
      "react-refresh/only-export-components": [
        "warn",
        { allowConstantExport: true },
      ],

      // Variables
      "no-unused-vars": [
        "error",
        {
          varsIgnorePattern: "^_",
          argsIgnorePattern: "^_",
          ignoreRestSiblings: true,
        },
      ],
      "no-undef": "error",
      "no-use-before-define": [
        "error",
        { functions: false, classes: true, variables: true },
      ],

      // Best Practices
      "no-console": ["warn", { allow: ["warn", "error"] }],
      "no-debugger": "error",
      "no-alert": "warn",
      "no-var": "error",
      "prefer-const": "error",
      "prefer-arrow-callback": "warn",
      "no-duplicate-imports": "error",
      "no-template-curly-in-string": "error",
      "no-unreachable": "error",
      "no-unreachable-loop": "error",
      "no-unsafe-optional-chaining": "error",
      "no-unused-private-class-members": "error",
      "require-atomic-updates": "error",

      // Code Quality
      eqeqeq: ["error", "always", { null: "ignore" }],
      "no-eval": "error",
      "no-implied-eval": "error",
      "no-new-func": "error",
      "no-return-await": "error",
      "no-throw-literal": "error",
      "prefer-promise-reject-errors": "error",
      "no-async-promise-executor": "error",
      "no-await-in-loop": "warn",
      "no-promise-executor-return": "error",

      // Styling
      "no-trailing-spaces": "error",
      "no-multiple-empty-lines": ["error", { max: 1, maxEOF: 0 }],
      "comma-dangle": ["error", "only-multiline"],
      semi: ["error", "always"],
      quotes: ["error", "double", { avoidEscape: true }],

      // Security
      "no-script-url": "error",
    },
    settings: {
      react: {
        version: "detect",
      },
    },
  },
];
