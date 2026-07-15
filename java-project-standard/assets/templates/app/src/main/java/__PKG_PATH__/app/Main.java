package __PKG__.app;

import __PKG__.domain.ProviderException;
import __PKG__.kernel.Log;

/** Entry point. Loads config, wires providers by config, runs the mock path offline. */
public final class Main {
  private Main() {}

  public static void main(String[] args) throws ProviderException {
    Wiring.Components components = Wiring.wire();
    Log.info("app", "started with llmProvider=" + components.config().llmProvider());
    Log.info("app", "llm says: " + components.llm().complete("hello"));
  }
}
