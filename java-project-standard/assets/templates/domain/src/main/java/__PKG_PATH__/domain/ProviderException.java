package __PKG__.domain;

/**
 * Normalized error at the provider (LLM / Embedder / real SDK) boundary. Sealed, so a caller that
 * maps or switches over it is checked for exhaustiveness by the compiler (Java 21 pattern
 * matching).
 */
public abstract sealed class ProviderException extends Exception
    permits ProviderException.MissingCredentials,
        ProviderException.Transport,
        ProviderException.InvalidResponse {

  private ProviderException(String message) {
    super(message);
  }

  /** Missing credentials (e.g. no API key configured). */
  public static final class MissingCredentials extends ProviderException {
    public MissingCredentials(String detail) {
      super(detail);
    }
  }

  /** Remote / transport-layer failure. */
  public static final class Transport extends ProviderException {
    public Transport(String detail) {
      super(detail);
    }
  }

  /** Response did not match expectations (empty result, malformed, etc.). */
  public static final class InvalidResponse extends ProviderException {
    public InvalidResponse(String detail) {
      super(detail);
    }
  }

  /** Exhaustive classification -- no default branch; adding a subtype breaks compilation here. */
  public String kind() {
    return switch (this) {
      case MissingCredentials ignored -> "missing_credentials";
      case Transport ignored -> "transport";
      case InvalidResponse ignored -> "invalid_response";
    };
  }
}
