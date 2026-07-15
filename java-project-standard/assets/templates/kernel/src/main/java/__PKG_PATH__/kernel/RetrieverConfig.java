package __PKG__.kernel;

/**
 * Retrieval configuration. Records have no field defaults, so the canonical constructor normalizes.
 */
public record RetrieverConfig(int topK, String rerankModel) {
  public RetrieverConfig {
    if (topK == 0) {
      topK = 5; // 0 == absent from JSON (Jackson's default for a primitive int)
    }
    if (rerankModel == null) {
      rerankModel = "mock-rerank";
    }
  }

  public static RetrieverConfig defaults() {
    return new RetrieverConfig(5, "mock-rerank");
  }
}
