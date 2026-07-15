package __PKG__.kernel;

/** Prompt loading/rendering errors. Sealed -&gt; exhaustive handling. */
public abstract sealed class PromptException extends RuntimeException
    permits PromptException.ResourceNotFound, PromptException.MissingVariable {

  private PromptException(String message) {
    super(message);
  }

  /** Bundled prompt resource not found on the classpath. */
  public static final class ResourceNotFound extends PromptException {
    public ResourceNotFound(String name) {
      super("prompt resource not found: " + name);
    }
  }

  /** Template referenced a variable that was not supplied. */
  public static final class MissingVariable extends PromptException {
    public MissingVariable(String key) {
      super("missing prompt variable: " + key);
    }
  }
}
