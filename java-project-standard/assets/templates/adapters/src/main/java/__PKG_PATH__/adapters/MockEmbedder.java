package __PKG__.adapters;

import __PKG__.domain.Embedder;
import java.util.ArrayList;
import java.util.List;

/** Deterministic mock embedder (same input -&gt; same output, preserves count). */
public final class MockEmbedder implements Embedder {
  private static final int SCALE = 1000;

  @Override
  public List<double[]> embed(List<String> texts) {
    List<double[]> vectors = new ArrayList<>(texts.size());
    for (String text : texts) {
      int sum = text.chars().sum();
      vectors.add(new double[] {(sum % SCALE) / (double) SCALE});
    }
    return List.copyOf(vectors);
  }
}
