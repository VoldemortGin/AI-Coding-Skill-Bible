package __PKG__.domain;

/**
 * Retrieval count with its constraint encoded in the record's compact constructor: an out-of-range
 * value fails at construction (parse, don't validate) rather than silently truncating downstream.
 */
public record TopK(int value) {
  public TopK {
    if (value < 1 || value > 100) {
      throw new IllegalArgumentException("topK out of range 1..100: " + value);
    }
  }
}
