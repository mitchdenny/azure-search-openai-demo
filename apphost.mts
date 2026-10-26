import { createBuilder } from "./.aspire/modules/aspire.mjs";

const builder = await createBuilder();

const containerName = "content";
const storage = await builder.addAzureStorage("storage");
const blobs = await storage.addBlobs("blobs");
const content = await storage.addBlobContainer(containerName);
const search = await builder.addAzureSearch("search");
const openai = await builder.addAzureOpenAI("openai");
const chat = await openai.addDeployment("chat", "gpt-4.1-mini", "2025-04-14");
const embeddings = await openai.addDeployment(
  "embeddings",
  "text-embedding-3-small",
  "1",
);

// Both services use loopback HTTP in development; Vite owns the browser origin
// and proxies API traffic so cookies and the MSAL redirect stay same-origin.
const backend = await builder
  .addUvicornApp("backend", "./app/backend", "main:app")
  .withVirtualEnvironment("../../.venv", { createIfNotExists: false })
  .withPip({ installArgs: ["--index-url", "https://pypi.org/simple"] })
  .withArgs(["--reload"])
  .withReference(content)
  .withReference(search)
  .withReference(chat)
  .withReference(embeddings)
  .withEnvironment("AZURE_STORAGE_ACCOUNT", storage.getOutput("name"))
  .withEnvironment("AZURE_STORAGE_CONTAINER", containerName)
  .withEnvironment("AZURE_SEARCH_SERVICE", search.getOutput("name"))
  .withEnvironment("AZURE_SEARCH_INDEX", "gptkbindex")
  .withEnvironment("OPENAI_HOST", "azure")
  .withEnvironment("AZURE_OPENAI_SERVICE", openai.getOutput("name"))
  .withEnvironment(
    "AZURE_OPENAI_CHATGPT_DEPLOYMENT",
    await chat.deploymentName.get(),
  )
  .withEnvironment("AZURE_OPENAI_CHATGPT_MODEL", await chat.modelName.get())
  .withEnvironment(
    "AZURE_OPENAI_EMB_DEPLOYMENT",
    await embeddings.deploymentName.get(),
  )
  .withEnvironment("AZURE_OPENAI_EMB_MODEL_NAME", await embeddings.modelName.get())
  .withEnvironment("AZURE_OPENAI_EMB_DIMENSIONS", "1536")
  .waitFor(blobs)
  .waitFor(content)
  .waitFor(search)
  .waitFor(chat)
  .waitFor(embeddings)
  .withHttpHealthCheck({ path: "/health" });

await builder
  .addViteApp("frontend", "./app/frontend")
  .withEnvironment("BACKEND_URL", backend.getEndpoint("http"))
  .withReference(backend)
  .waitFor(backend)
  .withHttpHealthCheck({ path: "/" })
  .withExternalHttpEndpoints();

await builder.build().run();
