package __PKG__.adapters;

import __PKG__.domain.Embedder;
import __PKG__.domain.Llm;

/**
 * Assembly seam: a config string selects an implementation. Default is mock; an unknown provider
 * fails loudly (never a silent fallback). This is the one place implementations are chosen.
 *
 * <p>Real backends (e.g. OpenAI) live in a gated sibling module (:adapters-openai) that is only
 * included when the {@code realProviders} Gradle property is set; unlock a branch below when it is.
 */
public final class ProviderFactory {
  private ProviderFactory() {}

  /**
   * Select an LLM implementation by provider id.
   *
   * @throws IllegalArgumentException when the provider is unknown (never silently falls back).
   */
  public static Llm makeLlm(String provider) {
    return switch (provider) {
      case "mock" -> new MockLlm();
      // case "openai" -> new OpenAiLlm(); // only with the gated :adapters-openai module
      default -> throw new IllegalArgumentException("unknown llmProvider: " + provider);
    };
  }

  /**
   * Select an Embedder implementation by provider id. Defaults to mock.
   *
   * @throws IllegalArgumentException when the provider is unknown.
   */
  public static Embedder makeEmbedder(String provider) {
    return switch (provider) {
      case "mock" -> new MockEmbedder();
      default -> throw new IllegalArgumentException("unknown embedder provider: " + provider);
    };
  }
}
