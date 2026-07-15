package __PKG__.kernel;

import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import org.jspecify.annotations.Nullable;

/**
 * Single source of global config: defaults &lt; configs/settings.json &lt; env (APP_ prefix, __
 * nesting).
 */
public record AppConfig(String llmProvider, RetrieverConfig retriever) {
  public AppConfig {
    if (llmProvider == null) {
      llmProvider = "mock";
    }
    if (retriever == null) {
      retriever = RetrieverConfig.defaults();
    }
  }

  public static AppConfig defaults() {
    return new AppConfig("mock", RetrieverConfig.defaults());
  }

  private static final ObjectMapper MAPPER =
      new ObjectMapper().configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);

  /**
   * Load config. Missing file -&gt; defaults; invalid JSON -&gt; loud failure (never silently
   * swallowed).
   */
  public static AppConfig load(String settingsPath, Map<String, String> env) {
    AppConfig base = defaults();
    Path path = Path.of(settingsPath);
    if (Files.isRegularFile(path)) {
      try {
        base = MAPPER.readValue(Files.readString(path), AppConfig.class);
      } catch (IOException e) {
        throw new UncheckedIOException("invalid config at " + settingsPath, e);
      }
    }
    return base.withEnvOverrides(env);
  }

  public static AppConfig load() {
    return load("configs/settings.json", System.getenv());
  }

  private AppConfig withEnvOverrides(Map<String, String> env) {
    String provider = llmProvider;
    int topK = retriever.topK();
    String rerankModel = retriever.rerankModel();

    @Nullable String p = env.get("APP_LLM_PROVIDER");
    if (p != null && !p.isEmpty()) {
      provider = p;
    }
    @Nullable String k = env.get("APP_RETRIEVER__TOP_K");
    if (k != null && !k.isEmpty()) {
      topK = Integer.parseInt(k);
    }
    @Nullable String r = env.get("APP_RETRIEVER__RERANK_MODEL");
    if (r != null && !r.isEmpty()) {
      rerankModel = r;
    }
    return new AppConfig(provider, new RetrieverConfig(topK, rerankModel));
  }
}
