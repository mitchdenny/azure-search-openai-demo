# RAG chat: Using reasoning models

Reasoning models spend more time processing the user's request. To use this feature,
configure an existing GPT-5-family deployment using `AZURE_OPENAI_CHATGPT_DEPLOYMENT`
and its matching `AZURE_OPENAI_CHATGPT_MODEL` in root `.env`. The example configuration
uses `gpt-4.1-mini`, not a reasoning model. Aspire does not deploy models.

## Supported models

We support the GPT-5 model family, but not the earlier o-series models, due to API incompatibilities.

## Configuring reasoning

1. **(Optional) Set default reasoning effort**

   You can configure how much effort the reasoning model spends on processing and understanding the user's request. Valid options are `minimal` (for base gpt-5 models), `none`, `low`, `medium`, and `high` (for gpt-5.1+), and `xhigh` (for gpt-5.4+). Reasoning effort defaults to `low` if not set.

   Set the environment variable for reasoning effort:

   ```shell
   AZURE_OPENAI_REASONING_EFFORT=medium
   ```

2. **Update the infrastructure and application:**

   Put the setting in `.env` and restart the AppHost to apply it.

3. **Try out the feature:**

   Open the web app and start a new chat. The reasoning model will be used for all Responses API requests, including the query rewriting step.

4. **Experiment with reasoning effort:**

   Select the developer options in the web app and change "Reasoning Effort". The available options depend on the deployed model. This will override the default reasoning effort of "low".

   ![Reasoning configuration screenshot](./images/reasoning.png)

5. **Understand token usage:**

   The reasoning models use additional billed tokens behind the scenes for the thinking process.
   To see the token usage, select the lightbulb icon on a chat answer. This will open the "Thought process" tab, which shows the reasoning model's thought process and the token usage for each response.

   ![Thought process token usage](./images/token-usage.png)
