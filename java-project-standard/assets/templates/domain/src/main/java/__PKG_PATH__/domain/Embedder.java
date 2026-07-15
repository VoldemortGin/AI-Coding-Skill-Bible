package __PKG__.domain;

import java.util.List;

/** Text embedding port. */
@FunctionalInterface
public interface Embedder {
  /**
   * Embed a batch of texts; returns one vector per input, in order.
   *
   * @throws ProviderException when the provider call fails (normalized at the adapter boundary).
   */
  List<double[]> embed(List<String> texts) throws ProviderException;
}
