package __PKG__.app;

import __PKG__.adapters.ProviderFactory;
import __PKG__.domain.Embedder;
import __PKG__.domain.Llm;
import __PKG__.kernel.AppConfig;

/**
 * Manual composition root: the one place implementations are selected by config. Kept
 * framework-free on purpose -- a hand-written wiring function is enough at this size. When wiring
 * outgrows it (many singletons, scopes, lifecycles), introduce a DI container here and nowhere
 * else, so the rest of the code keeps depending only on ports.
 */
public final class Wiring {
  private Wiring() {}

  /** The wired object graph. */
  public record Components(AppConfig config, Llm llm, Embedder embedder) {}

  public static Components wire(AppConfig config) {
    return new Components(
        config,
        ProviderFactory.makeLlm(config.llmProvider()),
        ProviderFactory.makeEmbedder(config.llmProvider()));
  }

  public static Components wire() {
    return wire(AppConfig.load());
  }
}
