import { existsSync, readFileSync } from "node:fs";
import { parseEnv } from "node:util";
import { createBuilder } from "./.aspire/modules/aspire.mjs";

const builder = await createBuilder();
const envFile = new URL("./.env", import.meta.url);
const configuration = {
  ...(existsSync(envFile) ? parseEnv(readFileSync(envFile, "utf8")) : {}),
  ...process.env,
};

const required = [
  "AZURE_STORAGE_ACCOUNT",
  "AZURE_STORAGE_CONTAINER",
  "AZURE_SEARCH_SERVICE",
  "AZURE_SEARCH_INDEX",
  "AZURE_OPENAI_CHATGPT_MODEL",
];
const openaiHost = configuration.OPENAI_HOST || "azure";
if (openaiHost === "azure" || openaiHost === "azure_custom") {
  required.push(
    openaiHost === "azure" ? "AZURE_OPENAI_SERVICE" : "AZURE_OPENAI_CUSTOM_URL",
    "AZURE_OPENAI_CHATGPT_DEPLOYMENT",
  );
  if (configuration.USE_VECTORS?.toLowerCase() !== "false") {
    required.push("AZURE_OPENAI_EMB_DEPLOYMENT");
  }
} else if (openaiHost === "openai") {
  required.push("OPENAI_API_KEY");
} else if (openaiHost === "local") {
  required.push("OPENAI_BASE_URL");
} else {
  throw new Error(
    `Unsupported OPENAI_HOST: ${openaiHost}. Use azure, azure_custom, openai, or local.`,
  );
}
const missing = required.filter((name) => !configuration[name]);
if (missing.length) {
  throw new Error(
    `Missing configuration: ${missing.join(", ")}. See .env.example and docs/localdev.md.`,
  );
}

// Both services use loopback HTTP in development; Vite owns the browser origin
// and proxies API traffic so cookies and the MSAL redirect stay same-origin.
const backend = await builder
  .addUvicornApp("backend", "./app/backend", "main:app")
  .withVirtualEnvironment("../../.venv")
  .withPip()
  .withArgs(["--reload"])
  .withHttpHealthCheck({ path: "/health" });

for (const [name, value] of Object.entries(configuration)) {
  if (
    value !== undefined &&
    /^(AZURE_|OPENAI_|USE_|RAG_|KB_FIELDS_|ENABLE_LANGUAGE_PICKER$|AGENTIC_|APPLICATIONINSIGHTS_CONNECTION_STRING$|APP_LOG_LEVEL$|FOUNDRY_|ALLOWED_ORIGIN$|CSV_MAX_PAGE_CHARS$|RUNNING_IN_PRODUCTION$|WEBSITE_)/.test(
      name,
    )
  ) {
    const secret = /KEY|SECRET|CONNECTION_STRING/.test(name);
    const parameter = await builder.addParameter(
      name.toLowerCase().replaceAll("_", "-"),
      { value, secret },
    );
    await backend.withEnvironment(name, parameter);
  }
}

await builder
  .addViteApp("frontend", "./app/frontend")
  .withEnvironment("BACKEND_URL", backend.getEndpoint("http"))
  .withReference(backend)
  .waitFor(backend)
  .withHttpHealthCheck({ path: "/" })
  .withExternalHttpEndpoints();

await builder.build().run();
