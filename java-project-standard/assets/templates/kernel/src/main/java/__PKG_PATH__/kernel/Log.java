package __PKG__.kernel;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Centralized logging over the SLF4J facade. Privacy is the API shape: payloads (answers, source
 * text, vectors, user input) have no parameter to pass in -- only codes/counts/versions.
 */
public final class Log {
  private static final Logger LOGGER = LoggerFactory.getLogger("app");

  private Log() {}

  public static void info(String category, String message) {
    LOGGER.info("[{}] {}", category, message);
  }

  public static void error(String category, String message) {
    LOGGER.error("[{}] {}", category, message);
  }

  /** Record one provider call's provenance -- codes/counts/versions only, never payload. */
  public static void logProvenance(String source, String impl, String version, int count) {
    LOGGER.info("provenance source={} impl={} version={} count={}", source, impl, version, count);
  }
}
