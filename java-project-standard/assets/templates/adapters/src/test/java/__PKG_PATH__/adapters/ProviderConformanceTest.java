package __PKG__.adapters;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import __PKG__.domain.Embedder;
import __PKG__.domain.Llm;
import __PKG__.domain.ProviderException;
import java.util.List;
import java.util.Map;
import java.util.function.Supplier;
import org.junit.jupiter.api.Test;

/**
 * Conformance kit: every type claiming to implement a port (the mock and any real backend) runs the
 * same behavioral invariants -- hot-swapping is only safe when all plugs behave alike. Add a real
 * adapter's supplier to the maps below and it reuses these assertions unchanged.
 */
class ProviderConformanceTest {
  private static final Map<String, Supplier<Embedder>> EMBEDDERS =
      Map.of("MockEmbedder", MockEmbedder::new);
  private static final Map<String, Supplier<Llm>> LLMS = Map.of("MockLlm", MockLlm::new);

  @Test
  void embedderIsDeterministic() throws ProviderException {
    for (var entry : EMBEDDERS.entrySet()) {
      Embedder embedder = entry.getValue().get();
      List<double[]> first = embedder.embed(List.of("hello", "world"));
      List<double[]> second = embedder.embed(List.of("hello", "world"));
      assertEquals(first.size(), second.size(), entry.getKey());
      for (int i = 0; i < first.size(); i++) {
        assertArrayEquals(first.get(i), second.get(i), entry.getKey() + " must be deterministic");
      }
    }
  }

  @Test
  void embedderPreservesInputCount() throws ProviderException {
    for (var entry : EMBEDDERS.entrySet()) {
      assertEquals(3, entry.getValue().get().embed(List.of("a", "b", "c")).size(), entry.getKey());
    }
  }

  @Test
  void embedderReturnsNonEmptyVectors() throws ProviderException {
    for (var entry : EMBEDDERS.entrySet()) {
      for (double[] vector : entry.getValue().get().embed(List.of("x"))) {
        assertTrue(vector.length > 0, entry.getKey());
      }
    }
  }

  @Test
  void llmReturnsNonEmptyCompletion() throws ProviderException {
    for (var entry : LLMS.entrySet()) {
      assertTrue(!entry.getValue().get().complete("ping").isEmpty(), entry.getKey());
    }
  }
}
