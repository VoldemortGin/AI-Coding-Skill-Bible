package __PKG__.domain;

/** Text generation port. Narrow interface; failures normalize to {@link ProviderException}. */
@FunctionalInterface
public interface Llm {
  /**
   * Generate a completion for the given prompt.
   *
   * @throws ProviderException when the provider call fails (normalized at the adapter boundary).
   */
  String complete(String prompt) throws ProviderException;
}
